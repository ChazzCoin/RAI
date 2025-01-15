# from F import DICT
# from bs4 import BeautifulSoup
# import re
# from F.LOG import Log
#
# import threading
# from typing import Set, List, Optional, Dict, Any
# from urllib.parse import urlparse
#
# from pydantic import BaseModel, Field
#
# from rai.data.web.WebDrive import RaiWebDriver
#
# Log = Log("RaiWebExtraction")
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.service import Service as ChromeService
# from webdriver_manager.chrome import ChromeDriverManager
#
# from rai.data import RaiPath, RaiDirectories
# import time
# from selenium.common.exceptions import (
#     WebDriverException,
#     TimeoutException,
#     NoSuchElementException,
# )
#
# from rai.data.loaders.rai_loaders.JsonlDataLoader import JSONLDataLoader
#
#
#
#
# """ Master Web Crawler """
# class RaiWebExtractor(RaiWebDriver):
#     scrape_limit = 0
#     scrape_count = 0
#     current_site_name = ""
#     to_visit_urls: Set[str] = set()
#     output_dir:RaiPath
#     output_file:RaiPath
#
#     def __init__(self, base_url: str, output_dir:str=None):
#         super(RaiWebExtractor, self).__init__()
#         if output_dir is None:
#             output_dir = RaiDirectories.output()
#         self.url = RaiUrl(base_url)
#         self.output_dir = RaiPath(output_dir)
#         self.current_site_name = self.url.site_name
#         self.domain_name = self.url.savable_name
#         self.output_file = RaiPath(RaiPath.join_path(self.output_dir, RaiPath.ADD_JSONL_EXT(self.domain_name)))
#         self.to_visit_urls = {self.url}
#         self.data_lock = threading.Lock()
#         self.output_dir.verify_create_directory()
#         self._load_existing_data()
#
#     @classmethod
#     def save(cls, url, page_limit:int=1):
#         newcls = cls(url)
#         newcls.scrape_limit = page_limit
#         newcls.crawl()
#         return newcls
#
#     def _load_existing_data(self):
#         self.visited_urls = JSONLDataLoader.load_file(self.output_file)
#
#     def _save_data(self, data: dict):
#         with self.data_lock: JSONLDataLoader.save_file(data, self.output_file)
#
#     def is_within_base_url(self, url: str) -> bool:
#         parsed_base = urlparse(self.url)
#         parsed_url = urlparse(url)
#         return parsed_url.netloc == parsed_base.netloc
#
#     def filter_add_urls(self, new_links):
#         filtered_links = []
#         for link in new_links:
#             if self.is_within_base_url(link):
#                 filtered_links.append(link)
#         with self.data_lock:
#             for link in filtered_links:
#                 if link not in self.visited_urls:
#                     self.to_visit_urls.add(link)
#
#     @staticmethod
#     def clean_text(text: str) -> str:
#         # Implement your text cleaning logic here
#         text = ' '.join(text.split())
#         return text
#
#     @staticmethod
#     def form_data(url:str, details:dict, text:str):
#         return {
#             'url': url,
#             'title': DICT.get('title', details, url),
#             'content': text
#         }
#
#     def _scrape_page(self, url: str):
#         try:
#             results = self.open(url)
#             text = self.clean_text(results['content'])
#             details = results['details']
#             self.filter_add_urls(results['urls'])
#             if not text: return
#             data = self.form_data(url, details, text)
#             self._save_data(data)
#         except (WebDriverException, TimeoutException, NoSuchElementException) as e:
#             Log.e(f"Error scraping {url}: {e}")
#
#     def crawl(self):
#         while self.to_visit_urls:
#             if self.scrape_limit > 0:
#                 if self.scrape_count >= self.scrape_limit:
#                     break
#             current_url = self.to_visit_urls.pop()
#             if current_url in self.visited_urls:
#                 continue
#             Log.w(f"Scraping: {current_url}")
#             self.visited_urls.add(current_url)
#             self._scrape_page(current_url)
#             self.scrape_count += 1
#
#         # self.driver.quit()
#         Log.s("Crawling completed.")
#
#     def start(self):
#         crawl_thread = threading.Thread(target=self.crawl)
#         crawl_thread.start()
#         crawl_thread.join()
#
#
#
# if __name__ == '__main__':
#     # RaiWebExtractor.save('https://playmetrics.com/teams/194129/calendar', page_limit=1)
#     # RaiWebCrawler(base_url='https://academy.veo.co', output_dir='output').start()