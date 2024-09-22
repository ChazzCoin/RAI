import os
import json
import time
import threading
from typing import Set, List
from urllib.parse import urljoin, urlparse
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)
from bs4 import BeautifulSoup

""" Master """
class RaiCrawler:
    def __init__(self, base_url: str, output_dir: str = 'output'):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.domain_name = urlparse(self.base_url).netloc.replace('.', '_')
        self.output_file = os.path.join(self.output_dir, f"{self.domain_name}.json")
        self.visited_urls: Set[str] = set()
        self.to_visit_urls: Set[str] = set([self.base_url])
        self.data_lock = threading.Lock()
        self.driver = self._init_driver()
        self._prepare_output_directory()
        self._load_existing_data()

    def _prepare_output_directory(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        # driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver

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

    def _extract_links(self, soup: BeautifulSoup) -> List[str]:
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(self.base_url, href)
            if self._is_valid_url(full_url):
                links.append(full_url.split('#')[0].rstrip('/'))
        return links

    def _scrape_page(self, url: str):
        try:
            self.driver.get(url)
            time.sleep(2)  # Allow dynamic content to load
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract and clean text
            for script in soup(['script', 'style', 'noscript']):
                script.extract()
            text = soup.get_text(separator=' ')
            cleaned_text = self._clean_text(text)

            if not cleaned_text:
                return

            data = {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'content': cleaned_text
            }

            self._save_data(data)

            # Extract new links to visit
            new_links = self._extract_links(soup)
            with self.data_lock:
                for link in new_links:
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

        self.driver.quit()
        print("Crawling completed.")

    def start(self):
        crawl_thread = threading.Thread(target=self.crawl)
        crawl_thread.start()
        crawl_thread.join()


if __name__ == '__main__':
    RaiCrawler(base_url='https://www.parkcitysoccer.org/', output_dir='output').start()