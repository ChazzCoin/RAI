import os
import random
import sys
import time
import uuid

import psutil
import asyncio
import requests
from xml.etree import ElementTree

__location__ = os.path.dirname(os.path.abspath(__file__))
__output__ = os.path.join(__location__, "output")

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from rai.raigents.composers import IngestContentAgent
from rai.ingest.DataImport import RaiDataImporter
from rai.ingest.loaders.rai_loaders.BaseLoad import RaiDocCreator

# Append parent directory to system path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, CrawlResult


class RaiQuickCrawler(RaiDocCreator):
    parent_id = str(uuid.uuid4())
    start_url = ""
    raw_pages = {str:CrawlResult}
    pages = []
    all_links = []

    def __init__(self, file_path: str=""):
        super().__init__(file_path)

    async def url_recon(self, url: str):
        # Sets to manage URLs
        to_visit = set()  # Each element is a tuple of URLs to crawl in parallel.
        visited = set()  # Tracks URLs already visited or scheduled.

        # Initialize result storage
        self.all_links = []
        self.pages = []  # Ensure self.pages is defined for storing CrawlResult objects.

        # Validate and enqueue the initial URL
        if not url:
            print("Provided URL is empty or None. Exiting crawl.")
            return
        if url not in visited:
            visited.add(url)
            to_visit.add((url,))
            self.all_links.append(url)

        run_count = 0
        max_runs = 1  # Prevent infinite loops by capping iterations

        while to_visit and run_count < max_runs:
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
                            self.pages.append(crawl_result)
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

        return self.all_links
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
    def to_chroma(self, prefix):
        RaiDataImporter.import_web_docs(prefix, self.start_url, self.cache)

    def to_pages(self):
        parent_id = str(uuid.uuid4())
        count = 1
        for k, v in self.raw_pages.items():
            try:
                page = DocumentAnalysisAgent.analyze_text_async(
                    content=self.TEXT_CLEANER(v.markdown),
                    url=k,
                    page_title=k,
                    parent_id=parent_id,
                    page_id=str(uuid.uuid4()),
                    page_number=str(count),
                )
                page.title = ""
                page.url = k
                page.author = "RaiWebPageScrape"
                page.events = []
                page.body = v.markdown
                page.images = []
                page.images_content = []
                page.pdfs = []
                page.pdfs_content = []
                page.tables = []

                self.to_documents(page)
                count = count + 1
            except Exception as e:
                print(e)
                continue

    def to_page(self, url, result:CrawlResult):

        try:
            page = DocumentAnalysisAgent.analyze_text_async(
                content=self.TEXT_CLEANER(result.markdown),
                url=url,
                page_title=url,
                parent_id=self.parent_id,
                page_id=str(uuid.uuid4()),
                page_number=str(0),
            )
            page.title = ""
            page.url = url
            page.author = "RaiWebPageScrape"
            page.events = []
            page.body = result.markdown
            page.images = []
            page.images_content = []
            page.pdfs = []
            page.pdfs_content = []
            page.tables = []

            self.raw_pages[url] = result
            self.pages.append(page)
            self.to_documents(page)
        except Exception as e:
            print(e)
            return None

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
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, screenshot=True)

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


SITEMAP_URL = "https://birminghamunited.com"

# List of common browser User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_urls():
    """
    Fetches all URLs from the provided sitemap.xml, avoiding 403 errors.
    Uses dynamic User-Agent headers and retries.

    Returns:
        List[str]: List of extracted URLs
    """
    session = requests.Session()

    # Retry strategy to handle transient failures
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504, 403],  # Retry on these errors
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/"
    }

    try:
        print(f"Fetching sitemap from {SITEMAP_URL}")
        response = session.get(SITEMAP_URL, headers=headers, timeout=10)

        # Handle 403 errors by trying a different User-Agent
        if response.status_code == 403:
            print("403 Forbidden! Retrying with a different User-Agent...")
            headers["User-Agent"] = random.choice(USER_AGENTS)
            time.sleep(random.uniform(1, 3))  # Add a slight delay before retry
            response = session.get(SITEMAP_URL, headers=headers, timeout=10)

        response.raise_for_status()

        # Parse XML
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as e:
            print(f"Error parsing sitemap XML: {e}")
            return []

        # Auto-detect namespace
        namespace = None
        if root.tag.startswith("{"):
            namespace = {"ns": root.tag.split("}")[0].strip("{")}

        # Extract URLs
        urls = [loc.text for loc in root.findall(".//ns:loc", namespace)] if namespace else []
        print(f"Successfully fetched {len(urls)} URLs from sitemap.")

        return urls

    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
        return []

async def main():
    crawler = RaiQuickCrawler()
    urls = ["https://www.birminghamunited.com"]
    if urls:
        print(f"Found {len(urls)} URLs to crawl")
        await crawler.url_recon("https://www.birminghamunited.com")
        for item in crawler.pages:
            DocumentAnalysisAgent.analyze_text_async(content=item.markdown, image=item.screenshot)
        # await crawler.crawl_parallel(urls, max_concurrent=50)
        # crawler.to_chroma(prefix="busa2025.1")
    else:
        print("No URLs found to crawl")



if __name__ == "__main__":
    asyncio.run(main())
    # get_urls()