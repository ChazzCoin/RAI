import ast
import base64
import io
import os
import random
import sys
import time
import uuid
import psutil
import asyncio
import requests
from PIL import Image
from xml.etree import ElementTree

__location__ = os.path.dirname(os.path.abspath(__file__))
__output__ = os.path.join(__location__, "output")

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from rai.ingest.parsers.PdfDiver import RaiPdfDiver
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.DataImport import RaiDataImporter

# Append parent directory to system path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from typing import List, Tuple
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, CrawlResult


def validate_and_prepare_screenshot(screenshot_str: str) -> bytes:

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

class RaiWebAgent:
    parent_id = str(uuid.uuid4())
    start_url = ""
    raw_pages = {str:CrawlResult}
    book = {}
    pages = []
    all_links = []

    @classmethod
    def load_url(cls, url: str) -> 'RaiWebAgent':
        self = cls()
        self.start_url = url
        return self

    async def execute(self):
        # Sets to manage URLs
        to_visit = set()  # Each element is a tuple of URLs to crawl in parallel.
        visited = set()  # Tracks URLs already visited or scheduled.

        # Initialize result storage
        self.all_links = []
        self.pages = []  # Ensure self.pages is defined for storing CrawlResult objects.

        # Validate and enqueue the initial URL
        if not self.start_url:
            print("Provided URL is empty or None. Exiting crawl.")
            return
        if self.start_url not in visited:
            visited.add(self.start_url)
            to_visit.add((self.start_url,))
            self.all_links.append(self.start_url)

        run_count = 0
        max_runs = 1  # Prevent infinite loops by capping iterations

        while to_visit:
            run_count += 1
            print(f"Run {run_count}: Processing {len(to_visit)} URL group(s) in queue.")

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

                    content = crawl_result.markdown

                    p = {
                        "source": key,
                        "success": TextProcessor.content_is_valid(content),
                        "content": content,
                        "screenshot": crawl_result.screenshot,
                        "image": validate_and_prepare_screenshot(crawl_result.screenshot),
                        "pdf": crawl_result.pdf,
                        "crawl_result": crawl_result,

                    }
                    self.pages.append(p)
            except Exception as proc_exc:
                print("Error processing crawl results.", proc_exc)

            # Deduplicate new URLs for this crawl cycle
            new_links = list(set(new_links))
            if new_links:
                # Queue the newly discovered links as a new group (tuple)
                to_visit.add(tuple(new_links))

        if run_count >= max_runs:
            print("Maximum run count reached; terminating crawling to avoid potential infinite loop.")

        print(
            f"Crawling completed after {run_count} iterations. Total unique URLs discovered: {len(self.all_links)}")

        # Ensure all_links contains only unique URLs
        self.all_links = list(set(self.all_links))

        return self.pages
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


    def print_results(self):
        for k,v in self.raw_pages.items():
            if v:
                print("URL:", v.url, "\n")
                print(v.markdown)
                print("\n--------------\n")
                print(v.markdown_v2.raw_markdown)
                print("\n--------------\n")
                print(v.markdown_v2.references_markdown)
                print("\n--------------\n")
                print(v.markdown_v2.markdown_with_citations)

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
            print(
                f"{prefix} Current Memory: {current_mem // (1024 * 1024)} MB, Peak: {peak_memory // (1024 * 1024)} MB")

        # Minimal browser config
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,  # corrected from 'verbos=False'
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            pdf=True,
            screenshot=True,
            screenshot_wait_for=5,
            prettiify=True,
            wait_for_images=True,
        )

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
                    if isinstance(result, Exception):
                        print(f"Error crawling {url}: {result}")
                        fail_count += 1
                    elif result.success:
                        # self.to_page(url, result)
                        # if type(result) not in [CrawlResult]:
                        #     continue
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

async def main():
    urls = ["https://www.birminghamunited.com"]
    if urls:
        print(f"Found {len(urls)} URLs to crawl")
        crawler = RaiWebAgent.load_url("https://www.birminghamunited.com")
        await crawler.execute()
        for p in crawler.pages:
            img = p["image"]
            pdf = p["pdf"]
            pdr = RaiPdfDiver.load_pdf(pdf)
            book = pdr.run()
            Image.open(io.BytesIO(img)).show()
        print("Finished")
    else:
        print("No URLs found to crawl")



if __name__ == "__main__":
    asyncio.run(main())
    # get_urls()