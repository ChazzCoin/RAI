# import threading
# from F.LOG import Log
#
# # from rai.base.BaseLoaders import register_loader
# from rai.data.web.RaiUrl import RaiUrl
# from rai.data.web.driver.DriverPageScrape import RaiWebPageScrape
#
# Log = Log("RaiWebLoader")
#
#
# # @register_loader(name="web")
# class RaiWebLoader(RaiWebPageScrape):
#
#     def __init__(self, base_url: str, username=None, password=None):
#         super(RaiWebLoader, self).__init__()
#         self.setup_login(username, password)
#         self.url = RaiUrl(base_url)
#         self.current_site_name = self.url.site_name
#         self.domain_name = self.url.savable_name
#         self.to_visit_urls = {self.url}
#         self.visited_urls = set()  # track visited
#         self.documents = []        # store RaiDocument objects
#         self.data_lock = threading.Lock()
#         self.scrape_count = 0
#
#     @classmethod
#     def pipeline(cls, url: str, page_limit: int = 1, username=None, password=None):
#         extractor = cls(url, username=username, password=password)
#         extractor.scrape_limit = page_limit
#         extractor.crawl()
#         return extractor
#
#     def load(self):
#         if self.cache:
#             Log.i(f"Returning Cached Loader: [ {getattr(self, 'file_path', None)} ]")
#             return self.cache
#         return self.crawl()
#
#     def crawl(self):
#         """
#         Main loop: pop URLs from to_visit_urls, scrape them, and add discovered links.
#         Respects the scrape_limit to avoid infinite crawling.
#         """
#         while self.to_visit_urls:
#             if not self.scrape_limit > 0: break
#             if self.scrape_count >= self.scrape_limit: break
#             next_url = self.to_visit_urls.pop()
#             # If already visited, skip
#             if next_url in self.visited_urls: continue
#             Log.w(f"Crawling has Begun...")
#             self.current_url = next_url
#             self.visited_urls.add(next_url)
#             self.scrape_page(next_url)
#             self.scrape_count += 1
#
#         Log.s("Crawling completed.")
#         return self.cache
#
#
# if __name__ == '__main__':
#     email = "jperson@parkcitysoccer.org"
#     password = "Philly23!"
#     crawler = RaiWebCrawler.pipeline("https://playmetrics.com/teams/194123/summary", 10, username=None, password=None)
#     loader = crawler.load()
#     for item in loader:
#         print(item.page_content)