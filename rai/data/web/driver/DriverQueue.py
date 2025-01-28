from typing import Set, List

from F.LOG import Log
from collections import deque
from rai.data.web.WebModels import PageExtractDetails
from rai.data.web.driver.DriverHelper import WebBaseHelper
from urllib.parse import urlparse
Log = Log("WebMaster")

class WebBaseQueue(WebBaseHelper):
    start_domain = None
    all_extracted_urls: set[str] = set()
    to_visit_urls: Set[str] = set()
    visited_urls: Set[str] = set()
    recon_queue = deque()
    scrape_limit = 0
    scrape_count = 0
    current_url = ""
    current_site_name = ""
    pages: [PageExtractDetails] = []

    @property
    def irrelevant_domains(self):
        return [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com',
            'ads', 'adservice', 'doubleclick.net', 'tracking', 'google-analytics', 'privacy',
            'help', 'account', 'terms'
        ]

    def is_in_domain(self, url):
        if not self.start_domain:
            return True  # If domain not set, skip check
        return urlparse(url).netloc == self.start_domain

    def add_update_recon_queue(self, url):
        if self.is_in_domain(url):
            if url not in self.to_visit_urls:
                self.recon_queue.append(url)
                self.to_visit_urls.add(url)
    def add_update_crawler_queue(self, new_links: List[str]):
        filtered_links = []
        for link in new_links:
            if str(link).endswith('.css'): continue
            if str(link).endswith('.js'): continue
            if str(link).endswith('.json'): continue
            if str(link).endswith('.svg'): continue
            if str(link).endswith('.jpeg'): continue
            if str(link).endswith('.jpg'): continue
            if str(link).endswith('.png'): continue
            if str(link).endswith('.pdf'): continue
            if str(link).endswith('.csv'): continue
            if self.is_within_base_url(self.current_url, link):
                filtered_links.append(link)

        for link in filtered_links:
            if link not in self.visited_urls:
                self.to_visit_urls.add(link)

    def add_irrelevant_domains(self, *domains:str):
        for domain in domains:
            self.irrelevant_domains.extend(domain)
    def is_irrelevant_link(self, url):
        return any(domain in url for domain in self.irrelevant_domains)

