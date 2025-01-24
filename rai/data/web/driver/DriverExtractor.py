import re
import time
from io import BytesIO
from typing import List

import pytesseract
import requests
from F import LIST
from F.LOG import Log
from PIL import Image
from bs4 import BeautifulSoup
from selenium.common import NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from rai.data.web.driver.DriverActions import WebBaseActions
from rai.data.web.soup.BaseExtractor import WebSoupExtractor
from selenium.webdriver.support import expected_conditions as EC

from rai.data.parsers.Pdf import FPDF

Log = Log("WebBaseExtract")

class WebBaseExtract(WebBaseActions, WebSoupExtractor):

    @property
    def page_title(self): return self.driver.title
    """ yes URLS """
    def extract_urls(self):
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        relevant_urls = [
            link.get_attribute('href')
            for link in links
            if link.get_attribute('href') and not self.is_irrelevant_link(link.get_attribute('href'))
        ]
        return relevant_urls
    """ IMAGES """
    def extract_image_urls(self) -> List[str]:
        image_urls = set()

        # --- 1. Extract from <img> tags ---
        img_elements = self.driver.find_elements(By.TAG_NAME, "img")
        for img in img_elements:
            # Primary src attribute
            src = img.get_attribute("src")
            if src:
                image_urls.add(src)
            # Lazy-loaded images might be in a data-src attribute
            data_src = img.get_attribute("data-src")
            if data_src:
                image_urls.add(data_src)
            # Some libraries might use other data attributes like data-lazy
            data_lazy = img.get_attribute("data-lazy")
            if data_lazy:
                image_urls.add(data_lazy)

        # --- 2. Extract from elements with inline styles (e.g., background images) ---
        # This finds all elements that have a style attribute set.
        styled_elements = self.driver.find_elements(By.XPATH, "//*[@style]")
        # A regex pattern to extract url(...) values from style attributes.
        background_image_regex = re.compile(r'url\(["\']?(.*?)["\']?\)')
        for elem in styled_elements:
            style = elem.get_attribute("style")
            if style:
                matches = background_image_regex.findall(style)
                for m in matches:
                    if m:
                        image_urls.add(m)

        # --- 3. Extract from <picture> elements and <source> tags (srcset) ---
        picture_elements = self.driver.find_elements(By.TAG_NAME, "picture")
        for picture in picture_elements:
            source_elements = picture.find_elements(By.TAG_NAME, "source")
            for source in source_elements:
                srcset = source.get_attribute("srcset")
                if srcset:
                    # srcset may contain multiple URLs separated by commas.
                    urls = [u.split()[0].strip() for u in srcset.split(",")]
                    for u in urls:
                        if u:
                            image_urls.add(u)

        # Convert the set to a list before returning
        return list(image_urls)
    def extract_text_from_image_urls(self, image_urls):
        image_texts = []
        for img in image_urls:
            temp = self.extract_text_from_image(img)
            if temp and temp != '' and not self.string_length_is_within(temp):
                print(temp)
                image_texts.append(temp)
        return image_texts
    @staticmethod
    def extract_text_from_image(image_url: str) -> str:
        """
        Given an image URL, download the image and run OCR using pytesseract.
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            image_bytes = BytesIO(response.content)
            image = Image.open(image_bytes)
            extracted_text = pytesseract.image_to_string(image)
            return extracted_text
        except Exception as e:
            Log.e("Image Processing Error", e)
            return ""

    """ PDFS """

    def extract_pdf_urls(self) -> List[str]:
        """
        Extracts PDF URLs from the current page by searching for <a> elements with href attributes ending in .pdf.

        Returns:
            A list of unique PDF URLs.
        """
        pdf_urls = set()
        # Find all anchor tags
        links = self.driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and re.search(r'\.pdf(\?.*)?$', href, re.IGNORECASE):
                pdf_urls.add(href)
        return list(pdf_urls)

    def extract_text_from_pdf_urls(self, pdf_urls: List[str]) -> List[str]:
        pdf_texts = []
        for pdf in pdf_urls:
            temp = self.extract_text_from_pdf(pdf)
            if temp and temp != '':
                print(temp)
                pdf_texts.append(temp)
        return pdf_texts

    @staticmethod
    def extract_text_from_pdf(pdf_url: str) -> str:
        """
        Given a PDF URL, download the PDF and extract text from its pages using PyPDF2.
        """
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
            pdf_bytes = BytesIO(response.content)
            return FPDF.extract_text_from_pdf(bytes=pdf_bytes)
        except Exception as e:
            Log.e("PDF Processing Error", e)
            return ""
    """ yes TABLES """
    def extract_all_tables(self, table_elem=None):
        # 1. Find all tables in the DOM
        table_elements = table_elem if table_elem else self.driver.find_elements(By.TAG_NAME, "table")

        all_parsed_tables = []
        for table in table_elements:
            header_cells = []
            try:
                thead = table.find_element(By.TAG_NAME, "thead")
                header_rows = thead.find_elements(By.TAG_NAME, "tr")
                if header_rows:
                    header_cells = header_rows[0].find_elements(By.CSS_SELECTOR, "th, td")
            except NoSuchElementException:
                pass

            if not header_cells:
                try:
                    first_row = table.find_element(By.TAG_NAME, "tr")
                    header_cells = first_row.find_elements(By.CSS_SELECTOR, "th, td")
                except NoSuchElementException:
                    all_parsed_tables.append([])
                    continue

            # Extract header names (text)
            headers = [cell.text.strip() for cell in header_cells]

            data_rows = []
            try:
                tbody = table.find_element(By.TAG_NAME, "tbody")
                data_rows = tbody.find_elements(By.TAG_NAME, "tr")
            except NoSuchElementException:
                # No <tbody>, fallback to all <tr> in the table
                data_rows = table.find_elements(By.TAG_NAME, "tr")

            if data_rows:
                first_data_row_text = [c.text.strip() for c in data_rows[0].find_elements(By.CSS_SELECTOR, "th, td")]
                if first_data_row_text == headers:
                    data_rows = data_rows[1:]

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
        return LIST.flatten(all_parsed_tables)

    """ TBD """
    def extract_metadata(self) -> [{}]:
        metas = self.driver.find_elements(By.TAG_NAME, 'meta')
        core_details = {}
        meta_tags = []
        for meta in metas:
            name = meta.get_attribute('name')
            property_ = meta.get_attribute('property')
            content = meta.get_attribute('content')

            if name == 'author' and content:
                core_details['author'] = content
            if (name == 'date' or property_ == 'article:published_time') and content:
                core_details['date'] = content
            # Collect other meta tags if needed (like description, keywords)
            if name and content:
                meta_tags.append({name: content})
        return meta_tags

    """ INDUSTRY CUSTOM """
    def extract_events(self):
        return LIST.flatten(LIST.merge_lists(self._extract_calendar_events(), self._extract_table_events()))
    def _extract_calendar_events(self):
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
        return events_data
    def _extract_table_events(self):
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
        return events

