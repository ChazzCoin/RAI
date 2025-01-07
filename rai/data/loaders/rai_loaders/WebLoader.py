import threading
import time
from typing import Set, List
from urllib.parse import urlparse

from F import DICT, LIST
from F.LOG import Log
from langchain_core.document_loaders import BaseLoader
from pydantic import BaseModel
from selenium.webdriver.common.by import By

from rai.RAG.CDocs import RaiChromaDBDocumentManager
from rai.agents.RaiAgents import AgentCategorizer
from rai.agents.Tools import YouthSoccerWebsiteCategories
from rai.data.DataUtilities import ensure_string_for_chroma
Log = Log("RaiWebLoader")
from selenium.common import WebDriverException, TimeoutException, NoSuchElementException

from rai.data.extraction.RaiWebExtraction import RaiWebDriver, RaiUrl, remove_non_printable_ascii, WebPageDetails
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader




class RaiWebLoader(RaiWebDriver, BaseLoader):
    cache:[] = []

    """
    Master Web Crawler that scrapes a given base_url, extracting page content
    into RaiDocument objects stored in memory for later use (e.g., ChromaDB).
    """
    scrape_limit = 0
    scrape_count = 0
    current_url = ""
    current_site_name = ""
    to_visit_urls: Set[str] = set()
    visited_urls: Set[str] = set()
    documents: List['RaiLoaderDocument'] = []

    chromadb = None

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
        self.chromadb = RaiChromaDBDocumentManager.web("pcsc2025", YouthSoccerWebsiteCategories)

    @classmethod
    def run(cls, url: str, page_limit: int = 1, username=None, password=None):
        """
        Convenience method that instantiates RaiWebExtractor, sets the page limit,
        and runs the crawl. Returns the instance containing the documents.
        """
        extractor = cls(url, username=username, password=password)
        extractor.scrape_limit = page_limit
        extractor.crawl()
        return extractor

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {getattr(self, 'file_path', None)} ]")
            return self.cache
        return self.crawl()

    def is_within_base_url(self, candidate_url: str) -> bool:
        parsed_base = urlparse(str(self.url))     # ensure string
        parsed_candidate = urlparse(candidate_url)
        return parsed_candidate.netloc == parsed_base.netloc

    def filter_add_urls(self, new_links: List[str]):
        """
        Filters out links that are off-domain or already visited,
        then adds them to the to_visit_urls set.
        """
        filtered_links = []
        for link in new_links:
            if self.is_within_base_url(link):
                filtered_links.append(link)

        with self.data_lock:
            for link in filtered_links:
                if link not in self.visited_urls:
                    self.to_visit_urls.add(link)

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Basic text cleaning logic, e.g., removing extra whitespace.
        """
        text = remove_non_printable_ascii(text)
        return ' '.join(text.split())

    @staticmethod
    def form_data(url: str, details: dict, text: str) -> dict:
        """
        Creates a dictionary of scraped data for consistency.
        """
        return {
            'url': url,
            'title': DICT.get('title', details, url),
            'content': text
        }

    def _scrape_page(self, url: str):
        """
        Attempts to open and scrape a single page, extracting text & metadata.
        New URLs discovered on the page are filtered and queued for scraping.
        """
        try:
            self.open(url)
            details = self.current_url_details()
            details.content = self.clean_text(self.extract_content())
            details.urls = self.extract_urls()
            details.images = self.extract_images()
            self.extract_calendar_events()
            self.extract_table_events()
            self.extract_all_tables()
            self.filter_add_urls(details.urls)

            # If there's no text, skip creating a document
            if not details.content: return

            # Create a dictionary of relevant data
            details.metadata = RaiMetadataLoader().ai_genny(text=details.content)

            # Convert that dictionary into a RaiDocument
            """ Web Contents Loader """
            doc = RaiLoaderDocument(
                page_content=str(details.content),
                metadata=ensure_string_for_chroma(details.metadata)
            )
            self.cache.append(doc)

            """ Table Contents Loader """
            for tableItem in LIST.flatten(details.tables):
                table_doc = RaiLoaderDocument(
                    page_content=str(tableItem),
                    metadata=ensure_string_for_chroma(details.metadata)
                )
                self.cache.append(table_doc)

            """ Events Contents Loader """
            for eventItem in LIST.flatten(details.events):
                event_doc = RaiLoaderDocument(
                    page_content=str(eventItem),
                    metadata=ensure_string_for_chroma(details.metadata)
                )
                self.cache.append(event_doc)


        except (WebDriverException, TimeoutException, NoSuchElementException) as e:
            Log.e(f"Error scraping {url}: {e}")

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
            self.create_url_details(next_url)
            self.visited_urls.add(next_url)
            self._scrape_page(next_url)
            self.scrape_count += 1

        Log.s("Crawling completed.")
        self.chromadb.to_chroma(docs=self.cache)
        return self.cache

    def current_url_details(self) -> WebPageDetails:
        results = self.get_url_details(self.current_url)
        if results: return results
        return self.create_url_details(self.current_url)
    def extract_calendar_events(self):
        """
        Parses the current page DOM using Selenium, finding all calendar-event
        items. Returns a list of dictionaries, each containing:
          - weekday
          - day_number
          - event_name
          - start_time
          - end_time
          - attendance_count
          - location
          - description
        """
        # Locate all calendar event containers by their combined class name
        # Adjust as needed if the class name changes or is dynamic
        event_containers = self.driver.find_elements(
            By.CSS_SELECTOR, "div.calendar-event-box.clickable.show-desktop-view"
        )

        events_data = []
        for container in event_containers:
            event_info = {}

            # 1. Date Container
            try:
                date_container = container.find_element(By.CSS_SELECTOR, "div.date-container")
                weekday_el = date_container.find_element(By.CSS_SELECTOR, ".date-weekday")
                day_number_el = date_container.find_element(By.CSS_SELECTOR, ".date-number")

                event_info["weekday"] = weekday_el.text.strip()
                event_info["day_number"] = day_number_el.text.strip()
            except NoSuchElementException:
                event_info["weekday"] = None
                event_info["day_number"] = None

            # 2. Event Name
            try:
                name_el = container.find_element(By.CSS_SELECTOR, "a.event-name")
                event_info["event_name"] = name_el.text.strip()
            except NoSuchElementException:
                event_info["event_name"] = None

            # 3. Times (e.g. "7:30 PM – 8:30 PM")
            #    We'll look for a div with class="times"
            try:
                times_el = container.find_element(By.CSS_SELECTOR, "div.times")
                times_text = times_el.text.strip()
                if "–" in times_text:
                    start_time, end_time = times_text.split("–", maxsplit=1)
                    event_info["start_time"] = start_time.strip()
                    event_info["end_time"] = end_time.strip()
                else:
                    event_info["start_time"] = times_text
                    event_info["end_time"] = None
            except NoSuchElementException:
                event_info["start_time"] = None
                event_info["end_time"] = None

            # 4. Attendance Count
            #    This example locates: container -> .attendance-count -> <button> -> <span> 6 </span>
            try:
                attendance_el = container.find_element(By.CSS_SELECTOR, "div.attendance-count")
                count_btn = attendance_el.find_element(By.TAG_NAME, "button")
                # The second <span> inside the button often holds the numeric count
                spans = count_btn.find_elements(By.TAG_NAME, "span")
                if len(spans) > 1:
                    event_info["attendance_count"] = spans[1].text.strip()
                else:
                    event_info["attendance_count"] = None
            except NoSuchElementException:
                event_info["attendance_count"] = None

            # 5. Location
            try:
                location_link = container.find_element(By.CSS_SELECTOR, "a.address-link")
                # Inside that, look for the .address-detail element
                address_span = location_link.find_element(By.CSS_SELECTOR, ".address-detail")
                event_info["location"] = address_span.text.strip()
            except NoSuchElementException:
                event_info["location"] = None

            # 6. Description
            #    Typically under `div.info.description`
            try:
                desc_el = container.find_element(By.CSS_SELECTOR, "div.info.description")
                event_info["description"] = desc_el.text.strip()
            except NoSuchElementException:
                event_info["description"] = None

            events_data.append(event_info)
        self.current_url_details().events.extend(events_data)
        return events_data
    def extract_table_events(self):
        """
        Finds all 'clickable' table rows and extracts event details
        from each row. Returns a list of dicts, each representing one event.
        """

        # Locate all rows with <tr class="clickable">
        rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.clickable")

        events = []
        for row in rows:
            # For each row, create a dictionary to store data
            event_data = {}

            # Example fields to scrape; adjust based on your table’s structure
            # 1. Date/Time
            try:
                date_td = row.find_element(By.CSS_SELECTOR, 'td[data-label="Date/Time"]')
                event_data["date_time"] = date_td.text.strip()
            except NoSuchElementException:
                event_data["date_time"] = ""

            # 2. Opponent
            try:
                opponent_td = row.find_element(By.CSS_SELECTOR, 'td[data-label="Opponent"]')
                event_data["opponent"] = opponent_td.text.strip()
            except NoSuchElementException:
                event_data["opponent"] = ""

            # 3. Location
            try:
                location_td = row.find_element(By.CSS_SELECTOR, 'td[data-label="Location"]')
                event_data["location"] = location_td.text.strip()
            except NoSuchElementException:
                event_data["location"] = ""

            # 4. Attendance
            try:
                attendance_td = row.find_element(By.CSS_SELECTOR, 'td[data-label="Attendance"]')
                event_data["attendance"] = attendance_td.text.strip()
            except NoSuchElementException:
                event_data["attendance"] = ""

            # 5. Score
            try:
                score_td = row.find_element(By.CSS_SELECTOR, 'td[data-label="Score"]')
                event_data["score"] = score_td.text.strip()
            except NoSuchElementException:
                event_data["score"] = ""

            # You can also pull out other cells or data from the row as needed.
            # Just repeat the pattern using row.find_element with the appropriate CSS.

            events.append(event_data)
        self.current_url_details().events.extend(events)
        return events
    def extract_all_tables(self):
        # 1. Find all tables in the DOM
        table_elements = self.driver.find_elements(By.TAG_NAME, "table")

        all_parsed_tables = []

        for table in table_elements:
            # Try to locate a <thead> row for headers
            header_cells = []
            try:
                thead = table.find_element(By.TAG_NAME, "thead")
                header_rows = thead.find_elements(By.TAG_NAME, "tr")
                if header_rows:
                    # Use the first <tr> in <thead> as the header row
                    header_cells = header_rows[0].find_elements(By.CSS_SELECTOR, "th, td")
            except NoSuchElementException:
                # No <thead> found, we'll look for the first <tr> in the table
                pass

            if not header_cells:
                # Attempt to get the first row from the table as the header row
                # (could be in <tbody> or direct <tr> under <table>)
                try:
                    first_row = table.find_element(By.TAG_NAME, "tr")
                    header_cells = first_row.find_elements(By.CSS_SELECTOR, "th, td")
                except NoSuchElementException:
                    # If we can't find any row, this table is empty or malformed
                    all_parsed_tables.append([])
                    continue

            # Extract header names (text)
            headers = [cell.text.strip() for cell in header_cells]

            # 2. Gather table rows (excluding the header row if needed)
            #    We'll look in <tbody> first, otherwise all <tr> in the table
            data_rows = []
            try:
                tbody = table.find_element(By.TAG_NAME, "tbody")
                data_rows = tbody.find_elements(By.TAG_NAME, "tr")
            except NoSuchElementException:
                # No <tbody>, fallback to all <tr> in the table
                data_rows = table.find_elements(By.TAG_NAME, "tr")

            # If we used the first row as headers, skip it in data rows
            if data_rows:
                # Compare the first row's text to the headers we extracted
                # If it matches, we skip it
                # Alternatively, you could skip the first row unconditionally if you know
                # for sure that first row is the header row.
                first_data_row_text = [c.text.strip() for c in data_rows[0].find_elements(By.CSS_SELECTOR, "th, td")]
                # Heuristic: If the text matches the 'headers' list, skip row 0
                if first_data_row_text == headers:
                    data_rows = data_rows[1:]

            # 3. Build a list of dictionaries, each row is { header: cell_value }
            table_data = []
            for row in data_rows:
                cells = row.find_elements(By.CSS_SELECTOR, "th, td")
                if not cells:
                    continue

                row_dict = {}
                for i, cell in enumerate(cells):
                    header_key = headers[i] if i < len(headers) else f"Column {i + 1}"
                    row_dict[header_key] = cell.text.strip()

                # Exclude empty row checks if needed (some pages might have blank rows)
                if any(value for value in row_dict.values()):
                    table_data.append(row_dict)

            all_parsed_tables.append(table_data)

        self.current_url_details().tables.extend(all_parsed_tables)
        return all_parsed_tables
    def categorize_page(self, page_contents):
        return AgentCategorizer().run(page_contents, "Youth Soccer Club", YouthSoccerWebsiteCategories)


if __name__ == '__main__':
    email = "jperson@parkcitysoccer.org"
    password = "Philly23!"
    crawler = RaiWebLoader.run("https://playmetrics.com/club-admin/staff", 4, username=email, password=password)
    loader = crawler.load()
    for item in loader:
        print(item.page_content)