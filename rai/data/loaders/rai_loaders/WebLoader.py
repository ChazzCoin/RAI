import re
import threading
from typing import List
from F import DICT, LIST, DATE
from F.LOG import Log
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from rai.base.BaseAgents import RaiBaseAgent
from rai.base.BaseFormats import RaiMetadata
from rai.base.BaseLoaders import register_loader
from rai.data.loaders.rai_loaders.BaseLoad import RaiBaseLoader
from rai.data.utilities.DataUtilities import ensure_string_for_chroma
from selenium.common import WebDriverException, TimeoutException, NoSuchElementException
from rai.data.loaders.rai_loaders.BaseDoc import RaiLoaderDocument
from rai.data.web.BodyExtractor import WebBodyExtractor
from rai.data.web.WebDrive import RaiWebDriver, RaiUrl
from rai.data.web.WebExtractor import WebActionExtractor
from rai.data.web.WebModels import WebPageDetails

Log = Log("RaiWebLoader")

@register_loader(name="web")
class RaiWebLoader(RaiWebDriver, RaiBaseLoader):
    cache:[] = []
    documents: List['RaiLoaderDocument'] = []

    def __init__(self, base_url: str, username=None, password=None):
        super(RaiWebLoader, self).__init__()
        self.setup_login(username, password)
        self.url = RaiUrl(base_url)
        self.current_site_name = self.url.site_name
        self.domain_name = self.url.savable_name
        self.to_visit_urls = {self.url}
        self.visited_urls = set()  # track visited
        self.documents = []        # store RaiDocument objects
        self.data_lock = threading.Lock()
        self.scrape_count = 0

    @classmethod
    def pipeline(cls, url: str, page_limit: int = 1, username=None, password=None):
        extractor = cls(url, username=username, password=password)
        extractor.scrape_limit = page_limit
        extractor.crawl()
        return extractor

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {getattr(self, 'file_path', None)} ]")
            return self.cache
        return self.crawl()

    def generate_metadata(self, content:str):
        Log.i("Generating Metadata.")
        metadata: RaiMetadata = RaiBaseAgent.pipeline(name='metadata', user_prompt=content)
        meta = metadata.model_dump()
        meta = DICT.add_key_value('url', self.current_url, meta)
        meta = DICT.add_key_value('page_title', self.page_title, meta)
        return meta

    def to_documents(self, page: WebPageDetails):
        """ Web Contents Loader """
        Log.i("Creating Content Documents.")
        try:
            doc = RaiLoaderDocument(
                page_content=str(page.content),
                metadata=ensure_string_for_chroma(page.metadata)
            )
            self.cache.append(doc)
        except Exception as e:
            print(f"No Content. {e}")
        """ Table Contents Loader """
        Log.i("Creating Table Documents.")
        try:
            for tableItem in LIST.flatten(page.table_objs):
                table_doc = RaiLoaderDocument(
                    page_content=str(tableItem),
                    metadata=ensure_string_for_chroma(page.metadata)
                )
                self.cache.append(table_doc)
        except Exception as e:
            print(f"No Tables. {e}")
        """ Events Contents Loader """
        Log.i("Creating Event Documents.")
        try:
            for eventItem in LIST.flatten(page.events):
                event_doc = RaiLoaderDocument(
                    page_content=str(eventItem),
                    metadata=ensure_string_for_chroma(page.metadata)
                )
                self.cache.append(event_doc)
        except Exception as e:
            print(f"No Events. {e}")
        Log.i(f"Document Count: {len(self.cache)}")

    def select_max_items_per_page(self,
                                  select_locator=(By.TAG_NAME, "select"),
                                  table_locator=(By.ID, "dataTable"),
                                  timeout=15):
        """
        Finds a dropdown for items per page, selects the highest numeric option,
        and waits for the table to load accordingly.

        Parameters:
            driver: Selenium WebDriver instance.
            select_locator: Tuple for locating the dropdown. Default searches by <select> tag.
            table_locator: Tuple for locating the key table element that refreshes.
                           Adjust this locator to target the element that confirms the page load.
            timeout: Maximum number of seconds to wait for elements and conditions.
        """
        try:
            # Wait for the dropdown to be visible on the page
            dropdown = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(select_locator)
            )
            select = Select(dropdown)

            # Find the option with the highest numeric value.
            max_val = None
            max_text = None
            for option in select.options:
                # Clean up the option text and use regex to search for digits.
                option_text = option.text.strip()
                match = re.search(r'(\d+)', option_text)
                if match:
                    value = int(match.group(1))
                    if max_val is None or value > max_val:
                        max_val = value
                        max_text = option_text

            if max_text is not None:
                # Select the option with the highest value.
                print(f"Selecting '{max_text}' from the dropdown.")
                select.select_by_visible_text(max_text)
            else:
                print("No numeric options were found in the dropdown.")
                return

            # Wait until the table is refreshed.
            #
            # One strategy is to wait until the number of rows in the table is at least as high
            # as the number indicated by the dropdown. Adjust the logic if your table structure differs.
            def table_has_enough_rows(driver):
                try:
                    table = driver.find_element(*table_locator)
                    # Assuming that the table rows are within <tr> tags.
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    return len(rows) >= max_val
                except Exception:
                    return False

            WebDriverWait(self.driver, timeout).until(table_has_enough_rows)
            print(f"Table updated to show at least {max_val} items per page.")

        except TimeoutException:
            print("Timed out waiting for page elements or table to update.")
            # Here you might want to add any additional error handling.

    def _scrape_page(self, url: str):
        try:
            self.open(url)
            self.select_max_items_per_page()
            Log.i("Extracting Page.")
            urls = self.extract_urls()
            images = self.extract_image_urls()
            image_texts = self.extract_text_from_image_urls(images)
            event_extract = self.extract_events()
            table_objs = self.extract_all_tables()

            actions = WebActionExtractor.pipeline(self.driver.page_source)
            body = WebBodyExtractor.pipeline(self.driver.page_source)
            final_content = f"{body.combined_text}\n\n{' '.join(image_texts)}"
            event_pipeline = RaiBaseAgent.pipeline(name="events", user_prompt=final_content)
            events = LIST.merge_lists(event_pipeline.events, event_extract)
            print(final_content)
            self.add_urls_to_queue(urls)

            """ Web Metadata """
            metadata = self.generate_metadata(body.combined_text)
            page = WebPageDetails(
                url=url,
                title=self.page_title,
                author="RaiWebDriver",
                date=DATE.get_now_month_day_year_str(),
                content=final_content,
                body = body,
                actions = actions,
                urls=urls,
                tags=DICT.get_any(keys=("tags", "keywords"), dic=metadata, default=[]),
                images=images,
                images_content=image_texts,
                tables=table_objs,
                events=events,
                metadata=metadata
            )
            self.pages.append(page)
            self.to_documents(page)
            Log.s(f"Successfully Scraped Page: {url}")
        except (WebDriverException, TimeoutException, NoSuchElementException) as e:
            Log.e(f"Error Scraping {url}: {e}")

    def crawl(self):
        """
        Main loop: pop URLs from to_visit_urls, scrape them, and add discovered links.
        Respects the scrape_limit to avoid infinite crawling.
        """
        while self.to_visit_urls:
            if not self.scrape_limit > 0: break
            if self.scrape_count >= self.scrape_limit: break
            next_url = self.to_visit_urls.pop()
            # If already visited, skip
            if next_url in self.visited_urls: continue
            Log.w(f"Crawling has Begun...")
            self.current_url = next_url
            self.visited_urls.add(next_url)
            self._scrape_page(next_url)
            self.scrape_count += 1

        Log.s("Crawling completed.")
        return self.cache


if __name__ == '__main__':
    email = "jperson@parkcitysoccer.org"
    password = "Philly23!"
    crawler = RaiWebLoader.pipeline("https://parkcitysoccer.org", 100, username=None, password=None)
    loader = crawler.load()
    for item in loader:
        print(item.page_content)