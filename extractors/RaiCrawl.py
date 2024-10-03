import os
import json
import threading
from typing import Set, List
from urllib.parse import urljoin, urlparse

from F import DICT
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)
from bs4 import BeautifulSoup
from extractors.extract_url import selenium_get_core_page_details_v2

def base_url_extractor(url):
    return urlparse(url).netloc

""" Master """
class RaiCrawler:
    base = ""

    def __init__(self, base_url: str, output_dir: str = 'output'):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.base = base_url_extractor(self.base_url)
        self.domain_name = urlparse(self.base_url).netloc.replace('.', '_')
        self.output_file = os.path.join(self.output_dir, f"{self.domain_name}.jsonl")
        self.visited_urls: Set[str] = set()
        self.to_visit_urls: Set[str] = set([self.base_url])
        self.data_lock = threading.Lock()
        self._prepare_output_directory()
        self._load_existing_data()

    def is_within_base_site(self, url: str) -> bool:
        if self.base == base_url_extractor(url):
            return True
        return False

    def _prepare_output_directory(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_existing_data(self):
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        self.visited_urls.add(item['url'])
                    except json.JSONDecodeError:
                        continue

    def _save_data(self, data: dict):
        with self.data_lock:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')

    def _clean_text(self, text: str) -> str:
        # Implement your text cleaning logic here
        text = ' '.join(text.split())
        return text

    def _is_valid_url(self, url: str) -> bool:
        parsed_base = urlparse(self.base_url)
        parsed_url = urlparse(url)
        return parsed_url.netloc == parsed_base.netloc

    def _scrape_page(self, url: str):
        try:
            results = selenium_get_core_page_details_v2(url)
            text = results['content']
            details = results['details']
            new_links = results['urls']
            filtered_links = []
            for link in new_links:
                if self._is_valid_url(link):
                    filtered_links.append(link)

            cleaned_text = self._clean_text(text)

            if not cleaned_text:
                return

            data = {
                'url': url,
                'title': DICT.get('title', details, url),
                'content': cleaned_text
            }

            self._save_data(data)
            # Extract new links to visit
            with self.data_lock:
                for link in filtered_links:
                    if link not in self.visited_urls:
                        self.to_visit_urls.add(link)

        except (WebDriverException, TimeoutException, NoSuchElementException) as e:
            print(f"Error scraping {url}: {e}")

    def crawl(self):
        while self.to_visit_urls:
            current_url = self.to_visit_urls.pop()
            if current_url in self.visited_urls:
                continue

            print(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            self._scrape_page(current_url)

        # self.driver.quit()
        print("Crawling completed.")

    def start(self):
        crawl_thread = threading.Thread(target=self.crawl)
        crawl_thread.start()
        crawl_thread.join()


if __name__ == '__main__':
    RaiCrawler(base_url='https://academy.veo.co', output_dir='output').start()