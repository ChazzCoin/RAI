import ast
import base64
import io
import os
import sys
import threading
import uuid
import psutil
import asyncio
from PIL import Image
from abc import abstractmethod
from F import DICT
from rai.ingest.utilities.IngestModels import IngestBrief
from rai.ingest.utilities.TextUtils import TextProcessor
from typing import List, Optional, Dict
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, CrawlResult
# Append parent directory to system path
__location__ = os.path.dirname(os.path.abspath(__file__))
__output__ = os.path.join(__location__, "output")

from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


def validate_and_prepare_screenshot(screenshot_str: str) -> Optional[bytes]:
    if screenshot_str is None: return None
    screenshot_bytes = None

    # Case 1: Check if the string is a literal representation of a bytes object.
    if screenshot_str.startswith("b'") or screenshot_str.startswith('b"'):
        try:
            # Safely evaluate the literal to get a bytes object.
            screenshot_bytes = ast.literal_eval(screenshot_str)
            if not isinstance(screenshot_bytes, bytes):
                raise ValueError("Evaluated value is not of type bytes")
        except Exception as e:
            raise ValueError("Failed to convert byte string representation to bytes") from e
    else:
        # Case 2: Assume the screenshot is a base64 encoded string.
        try:
            screenshot_bytes = base64.b64decode(screenshot_str)
        except Exception as e:
            raise ValueError("Failed to decode base64 screenshot string") from e

    # Validate that the bytes represent a valid image.
    try:
        with Image.open(io.BytesIO(screenshot_bytes)) as img:
            img.verify()  # Will raise an exception if the image is invalid.
    except Exception as e:
        raise ValueError("The resulting bytes do not represent a valid image") from e

    return screenshot_bytes


WEB_CONFIG_REGISTRY = {}

def register_web_config(name: str):
    def decorator(cls):
        WEB_CONFIG_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator


class WebCrawlerConfig:
    # Minimal browser config

    @staticmethod
    @abstractmethod
    def is_single_run() -> bool: pass

    @staticmethod
    @abstractmethod
    def runs() -> int: pass

    @staticmethod
    @abstractmethod
    def max_concurrent() -> int: pass

    @staticmethod
    @abstractmethod
    def browser() -> BrowserConfig: pass

    @staticmethod
    @abstractmethod
    def crawl() -> CrawlerRunConfig: pass


class IngestWebSourceProvider:
    config: WebCrawlerConfig
    parent_id = str(uuid.uuid4())
    start_url = ""
    raw_pages = {str:CrawlResult}
    briefings = {}
    all_links = []

    @classmethod
    def get_registry(cls): return WEB_CONFIG_REGISTRY

    @staticmethod
    def get_config(name): return WEB_CONFIG_REGISTRY.get(name)[0]

    @staticmethod
    def execute(name, data_in) -> 'IngestWebSourceProvider':
        result_container = {}
        def thread_target(name, url):
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Run the async function until complete
                result = loop.run_until_complete(
                    IngestWebSourceProvider.execute_async(name, url)
                )
                result_container['result'] = result
            finally:
                loop.close()

        # Start the thread and wait for it to finish
        thread = threading.Thread(target=thread_target, args=(name, data_in))
        thread.start()
        thread.join()

        return result_container.get('result')
    @classmethod
    async def execute_async(cls, name, url: str) -> 'IngestWebSourceProvider':
        self = cls()
        self.start_url = url
        self.config = self.get_config(name)
        await self.run()
        return self

    @classmethod
    def load_url(cls, url: str, config:WebCrawlerConfig=None) -> 'IngestWebSourceProvider':
        self = cls()
        self.start_url = url
        self.config = config
        return self

    async def run_single(self) -> Optional[IngestBrief]:
        try:
            # Convert the tuple to a list if crawl_parallel expects a list
            result = await self.crawl_parallel([self.start_url], max_concurrent=1)
            crawl_result = DICT.get(self.start_url, result, None)
            body = WebBodyExtractor.pipeline(crawl_result.html)
            content = body.combined_text
            return IngestBrief(
                source=str(self.start_url),
                success=TextProcessor.content_is_valid(content),
                original_content=str(content),
                content=TextProcessor.NORMALIZER(content),
            )
        except Exception as crawl_exc:
            print("Error during parallel crawl execution.", crawl_exc)
            return None

    async def run(self) -> Dict[str, 'IngestBrief']:

        if self.config.is_single_run():
            brief = await self.run_single()
            self.briefings[self.start_url] = brief
            return brief

        to_visit = set()
        visited = set()

        self.all_links = []
        self.briefings = {}

        if not self.start_url:
            print("Provided URL is empty or None. Exiting crawl.")
            return {}
        if self.start_url not in visited:
            visited.add(self.start_url)
            to_visit.add((self.start_url,))
            self.all_links.append(self.start_url)

        while to_visit:

            if len(self.briefings) >= self.config.runs():
                break

            try:
                # Pop one group (tuple) of URLs for parallel crawling
                current_group = to_visit.pop()
            except KeyError:
                print("URL group queue is empty.")
                break

            if not current_group:
                print("Encountered an empty URL group; skipping.")
                continue

            try:
                # Convert the tuple to a list if crawl_parallel expects a list
                result = await self.crawl_parallel(list(current_group), max_concurrent=100)
            except Exception as crawl_exc:
                print("Error during parallel crawl execution.", crawl_exc)
                continue

            new_links = []
            try:
                # Process each URL's crawl result
                for key, crawl_result in result.items():
                    # Skip any invalid keys
                    if not str(key).startswith("http"):
                        continue

                    # Extract internal links; safeguard against missing keys
                    internal_links = crawl_result.links.get('internal', [])
                    for link in internal_links:
                        temp_url = link.get('href')
                        if temp_url and temp_url not in visited and self.should_add_link(temp_url):
                            visited.add(temp_url)
                            new_links.append(temp_url)
                            self.all_links.append(temp_url)

                    body = WebBodyExtractor.pipeline(crawl_result.html)
                    content = body.combined_text

                    try:
                        page = IngestBrief(
                            source=str(key),
                            success= TextProcessor.content_is_valid(content),
                            original_content=str(content),
                            content=TextProcessor.NORMALIZE_NEW_LINES(content),
                            page_screenshot=validate_and_prepare_screenshot(crawl_result.screenshot),
                            page_pdf=crawl_result.pdf
                        )
                        self.briefings[str(key)] = page
                    except Exception as e:
                        print("Failed to process page, falling back", e)
                        try:
                            page = IngestBrief(
                                source=str(key),
                                success=False,
                                original_content=str(content),
                                content=TextProcessor.NORMALIZE_NEW_LINES(content),
                            )
                            self.briefings[str(key)] = page
                        except Exception as e:
                            print("Failed to process page, completely", e)

            except Exception as proc_exc:
                print("Error processing crawl results.", proc_exc)

            # Deduplicate new URLs for this crawl cycle
            new_links = list(set(new_links))
            if new_links:
                # Queue the newly discovered links as a new group (tuple)
                to_visit.add(tuple(new_links))

        print("Crawling finished. Pages Extracted:", len(self.briefings.items()))
        # Ensure all_links contains only unique URLs
        self.all_links = list(set(self.all_links))

        return self.briefings

    def should_add_link(self, link) -> bool:
        if str(link).endswith('.css'): return False
        if str(link).endswith('.ico'): return False
        if str(link).endswith('.js'): return False
        if str(link).endswith('.json'): return False
        if str(link).endswith('.svg'): return False
        if str(link).endswith('.jpeg'): return False
        if str(link).endswith('.jpg'): return False
        if str(link).endswith('.png'): return False
        if str(link).endswith('.pdf'): return False
        if str(link).endswith('.csv'): return False
        if str(link).endswith('.doc'): return False
        if str(link).endswith('.docx'): return False
        if str(link).endswith('.xls'): return False
        if str(link).endswith('.xlsx'): return False
        return True

    async def crawl_parallel(self, urls: List[str], max_concurrent: int = 3):
        print("\n=== Parallel Crawling with Browser Reuse + Memory Check ===")
        self.start_url = urls[0]
        # We'll keep track of peak memory usage across all tasks
        peak_memory = 0
        process = psutil.Process(os.getpid())

        def log_memory(prefix: str = ""):
            nonlocal peak_memory
            current_mem = process.memory_info().rss  # in bytes
            if current_mem > peak_memory:
                peak_memory = current_mem
            print(f"{prefix} Current Memory: {current_mem // (1024 * 1024)} MB, Peak: {peak_memory // (1024 * 1024)} MB")

        # Minimal browser config
        browser_config = self.config.browser()
        crawl_config = self.config.crawl()

        # Create the crawler instance
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()

        try:
            # We'll chunk the URLs in batches of 'max_concurrent'
            success_count = 0
            fail_count = 0
            for i in range(0, len(urls), max_concurrent):
                batch = urls[i: i + max_concurrent]
                tasks = []

                for j, url in enumerate(batch):
                    # Unique session_id per concurrent sub-task
                    session_id = f"parallel_session_{i + j}"
                    task = crawler.arun(url=url, config=crawl_config, session_id=session_id)
                    tasks.append(task)

                # Check memory usage prior to launching tasks
                log_memory(prefix=f"Before batch {i // max_concurrent + 1}: ")

                # Gather results
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check memory usage after tasks complete
                log_memory(prefix=f"After batch {i // max_concurrent + 1}: ")

                # Evaluate results
                for url, result in zip(batch, results):
                    print("Crawled URL:", url)
                    if isinstance(result, Exception):
                        print(f"Error crawling {url}: {result}")
                        fail_count += 1
                    elif result.success:
                        self.raw_pages[url] = result
                        success_count += 1
                    else:
                        fail_count += 1

            print(f"\nSummary:")
            print(f"  - Successfully crawled: {success_count}")
            print(f"  - Failed: {fail_count}")

        finally:
            print("\nClosing crawler...")
            await crawler.close()
            # Final memory log
            log_memory(prefix="Final: ")
            print(f"\nPeak memory usage (MB): {peak_memory // (1024 * 1024)}")
        return self.raw_pages


@register_web_config(name="injection")
class WebCrawlerPlanDeep(WebCrawlerConfig):

    @staticmethod
    def is_single_run() -> bool: return True

    @staticmethod
    def runs() -> int: return 1

    @staticmethod
    def max_concurrent() -> int: return 100

    @staticmethod
    def browser() -> BrowserConfig:
        return BrowserConfig(
            user_data_dir="/Users/chazzromeo/Library/Caches/ms-playwright/chromium-1161/chrome-mac/Chromium.app",
            headless=True,
            light_mode=True,
            accept_downloads=False,
            downloads_path=None,
            verbose=False,  # corrected from 'verbos=False'
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )

    @staticmethod
    def crawl() -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            pdf=False,
            screenshot=False,
            screenshot_wait_for=0,
            prettiify=False,
            wait_for_images=False,
        )
@register_web_config(name="speed")
class WebCrawlerPlanDeep(WebCrawlerConfig):

    @staticmethod
    def is_single_run() -> bool: return False

    @staticmethod
    def runs() -> int: return 10

    @staticmethod
    def max_concurrent() -> int: return 100

    @staticmethod
    def browser() -> BrowserConfig:
        return BrowserConfig(
        headless=True,
        light_mode=True,
        accept_downloads=False,
        downloads_path=None,
        verbose=False,  # corrected from 'verbos=False'
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    @staticmethod
    def crawl() -> CrawlerRunConfig:
        return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        scan_full_page=True,
        pdf=False,
        screenshot=False,
        screenshot_wait_for=0,
        prettiify=False,
        wait_for_images=False,
    )

@register_web_config(name="deep")
class WebCrawlerPlanDeep(WebCrawlerConfig):

    @staticmethod
    def is_single_run() -> bool: return False

    @staticmethod
    def runs() -> int: return 500

    @staticmethod
    def max_concurrent() -> int: return 100

    @staticmethod
    def browser() -> BrowserConfig:
        return BrowserConfig(
            headless=True,
            light_mode=False,
            accept_downloads=True,
            downloads_path=__output__,
            verbose=False,  # corrected from 'verbos=False'
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
    @staticmethod
    def crawl() -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            pdf=True,
            screenshot=True,
            screenshot_wait_for=5,
            prettiify=True,
            wait_for_images=True,
        )

async def main():
    urls = ["https://www.birminghamunited.com"]
    if urls:
        print(f"Found {len(urls)} URLs to crawl")
        crawler = await IngestWebSourceProvider.execute_async("speed", "https://www.birminghamunited.com")
        print("Finished", len(crawler.briefings))
    else:
        print("No URLs found to crawl")



if __name__ == "__main__":
    # asyncio.run(main())
    # get_urls()
    results = IngestWebSourceProvider.execute('injection', 'https://www.wired.com/story/inside-the-telegram-groups-doxing-women-for-their-facebook-posts/')
    print(results)