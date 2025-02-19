import json
import re
from io import BytesIO
from typing import List

import pytesseract
import requests
from F import LIST
from F.LOG import Log
from PIL import Image
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from rai.ingest.web.driver.DriverActions import WebBaseActions
from rai.ingest.web.soup.BaseExtractor import WebSoupExtractor

from rai.ingest.parsers.Pdf import FPDF

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
    def extract_all_tables(self):
        full_table = []
        try:
            while True:
                tempTable = self.extract_page_table()
                if not tempTable: break
                full_table.append(tempTable)
                if not self.click_next_table_page(): break
                continue
        except Exception as e:
            print(e)
        return LIST.flatten(full_table)
    def extract_page_table(self, table_elem=None):
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
                    row_dict["parent"] = self.page_title or ""
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
    def extract_calendar_events(self):
        """
        Extracts all calendar events from the page, grouping them by
        Month/Year header (e.g. "January 2025") when possible, but still
        attempting to parse events dynamically (even if the header fails).

        Additionally, for each event container, we do a 'dynamic' pass:
        we inspect child elements, gather their classes, and store text
        in `event_info["dynamic_fields"]` under those class-based keys.
        """
        events_data = []

        # Grab all top-level "calendar-list" sections
        date_sections = self.driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'calendar') and contains(@class, 'list')]"
        )

        # If we find no sections, we could still try to parse all .calendar-event-box from entire page
        if not date_sections:
            events_data.extend(self._parse_events_fallback())
            return events_data

        for section in date_sections:
            # Try to find date headers (e.g. "January 2025", etc.)
            # date_headers = section.find_elements(By.CSS_SELECTOR, "div.date-header")
            date_headers = section.find_elements(
                By.XPATH,
                "//div[contains(@class, 'date') and contains(@class, 'header')]"
            )

            # If no headers are found, just parse all event boxes in this "calendar-list" as fallback
            if not date_headers:
                # Fallback: parse all clickable event boxes in `section` directly
                # event_boxes = section.find_elements(By.CSS_SELECTOR, "div.calendar-event-box.clickable")
                event_boxes = section.find_elements(
                    By.XPATH,
                    "//*[contains(@class, 'event') and contains(@class, 'clickable')]"
                )
                events_data.extend(
                    self._parse_events_without_header(event_boxes)
                )
                continue

            # Otherwise, handle normal header-based logic
            for i, header_el in enumerate(date_headers):
                month_year_text = header_el.text.strip()
                # if month_year_text == '':
                #     continue # e.g. "January 2025"
                event_boxes_in_this_header = []

                # Gather siblings until we reach the next date-header
                all_siblings = header_el.find_elements(By.XPATH, "./following-sibling::div")
                for sibling in all_siblings:
                    # If we find another date-header, that means stop
                    try:
                        sibling.find_element(By.CSS_SELECTOR, "div.date-header")
                        break
                    except NoSuchElementException:
                        pass

                    # Otherwise, gather event boxes
                    """
                    boxes = sibling.find_elements(
                                By.XPATH,
                                "//*[contains(@class, 'calendar-') and contains(@class, 'clickable')]"
                            )
                    """
                    try:
                        boxes = sibling.find_elements(By.CSS_SELECTOR, "div.calendar-event-box.clickable")
                        event_boxes_in_this_header.extend(boxes)
                    except NoSuchElementException:
                        continue

                # Parse each event box found under this month/year
                for container in event_boxes_in_this_header:
                    event_info = {}

                    # Store the extracted month_year from the header
                    event_info["month_year"] = month_year_text

                    # -------------------------
                    # 1. WEEKDAY / DAY NUMBER
                    # -------------------------
                    try:
                        date_container = container.find_element(By.CSS_SELECTOR, "div.date-container")
                        weekday_el = date_container.find_element(By.CSS_SELECTOR, ".date-weekday")
                        day_number_el = date_container.find_element(By.CSS_SELECTOR, ".date-number")
                        event_info["weekday"] = weekday_el.text.strip()
                        event_info["day_number"] = day_number_el.text.strip()
                    except NoSuchElementException:
                        event_info["weekday"] = None
                        event_info["day_number"] = None

                    # 2. EVENT NAME
                    try:
                        name_el = container.find_element(By.CSS_SELECTOR, "a.event-name")
                        event_info["event_name"] = name_el.text.strip()
                    except NoSuchElementException:
                        event_info["event_name"] = None

                    # ---------------------------------------------
                    # 3. TIMES (start_time, end_time, arrival_time)
                    # ---------------------------------------------
                    event_info["start_time"] = None
                    event_info["end_time"] = None
                    event_info["arrival_time"] = None
                    try:
                        times_el = container.find_element(By.CSS_SELECTOR, "div.times")
                        times_text = times_el.text.strip()
                        if "Arrive by" in times_text:
                            main_part, arrive_part = times_text.split("Arrive by", maxsplit=1)
                            event_info["arrival_time"] = arrive_part.replace(")", "").strip()
                            # strip parentheses from main_part as well
                            times_text = main_part.strip().replace("(", "").replace(")", "").strip()

                        if "–" in times_text:
                            start_time, end_time = times_text.split("–", maxsplit=1)
                            event_info["start_time"] = start_time.strip()
                            event_info["end_time"] = end_time.strip()
                        else:
                            event_info["start_time"] = times_text.strip()
                    except NoSuchElementException:
                        pass

                    # 4. ATTENDANCE COUNT
                    try:
                        attendance_el = container.find_element(By.CSS_SELECTOR, "div.attendance-count")
                        count_btn = attendance_el.find_element(By.TAG_NAME, "button")
                        spans = count_btn.find_elements(By.TAG_NAME, "span")
                        if len(spans) > 1:
                            event_info["attendance_count"] = spans[1].text.strip()
                        else:
                            event_info["attendance_count"] = None
                    except NoSuchElementException:
                        event_info["attendance_count"] = None

                    # 5. LOCATION
                    try:
                        location_link = container.find_element(By.CSS_SELECTOR, "a.address-link")
                        address_span = location_link.find_element(By.CSS_SELECTOR, ".address-detail")
                        event_info["location"] = address_span.text.strip()
                    except NoSuchElementException:
                        event_info["location"] = None

                    # 6. DESCRIPTION
                    try:
                        desc_el = container.find_element(By.CSS_SELECTOR, "div.info.description")
                        event_info["description"] = desc_el.text.strip()
                    except NoSuchElementException:
                        event_info["description"] = None

                    # 7. UNIFORM / EXTRA INFO
                    try:
                        uniform_el = container.find_element(
                                By.XPATH,
                                "//div[contains(@class, 'info') and contains(@class, 'uniform')]"
                            )
                        event_info["uniform_instructions"] = uniform_el.text.strip()
                    except NoSuchElementException:
                        event_info["uniform_instructions"] = None

                    # -------------------------
                    # 8. OPTIONAL: DYNAMIC FIELDS
                    # -------------------------
                    # We'll gather anything else we can from child elements,
                    # storing them in event_info["dynamic_fields"].
                    dynamic_dict = {}
                    all_descendants = container.find_elements(By.XPATH, ".//*")
                    for elem in all_descendants:
                        class_attr = elem.get_attribute("class") or ""
                        text_val = elem.text.strip()
                        if not text_val:
                            continue  # skip if empty

                        classes = class_attr.split()
                        for c in classes:
                            # Example: "date-weekday" => "date_weekday"
                            normalized_key = c.replace("-", "_")
                            # store in dynamic_dict
                            # if we want first occurrence only:
                            if normalized_key not in dynamic_dict:
                                dynamic_dict[normalized_key] = text_val

                    event_info["dynamic_fields"] = dynamic_dict
                    # Example "parent" if you want to store page title or other metadata:
                    event_info["parent"] = self.page_title
                    # Done - add to results
                    events_data.append(event_info)

        return events_data

    def _parse_events_without_header(self, event_boxes):
        """
        Fallback function if no headers exist: parse known fields
        dynamically from each box, no 'month_year' assigned.
        """
        events = []
        for container in event_boxes:
            event_info = {}

            # We'll skip 'month_year' because we don't have a date-header
            event_info["month_year"] = None

            # Try some known fields (like event_name)
            try:
                name_el = container.find_element(By.CSS_SELECTOR, "a.event-name")
                event_info["event_name"] = name_el.text.strip()
            except NoSuchElementException:
                event_info["event_name"] = None

            # (You could replicate more known-field logic here if desired.)
            # Or just do the dynamic approach:
            dynamic_dict = {}
            all_descendants = container.find_elements(By.XPATH, ".//*")
            for elem in all_descendants:
                class_attr = elem.get_attribute("class") or ""
                text_val = elem.text.strip()
                if not text_val:
                    continue
                for c in class_attr.split():
                    norm_key = c.replace("-", "_")
                    if norm_key not in dynamic_dict:  # store first occurrence
                        dynamic_dict[norm_key] = text_val

            event_info["dynamic_fields"] = dynamic_dict
            event_info["parent"] = self.page_title

            events.append(event_info)
        return events

    def _parse_events_fallback(self):
        """
        If no .calendar-list found at all, parse .calendar-event-box at page level
        (if that is a scenario for your app).
        """
        # Very similar to _parse_events_without_header
        all_boxes = self.driver.find_elements(By.CSS_SELECTOR, "div.calendar-event-box.clickable")
        return self._parse_events_without_header(all_boxes)

    def extract_table_data(self):
        try:
            # Locate the table container
            table = self.driver.find_element(By.CSS_SELECTOR, ".table-wrapper")

            # Extract header row (event types)
            headers = []
            event_columns = table.find_elements(By.CSS_SELECTOR, ".event-header")
            for col in event_columns:
                headers.append(col.text.strip())

            # Extract players data
            players_data = []
            player_rows = table.find_elements(By.CSS_SELECTOR, ".player-row")

            for row in player_rows:
                player = {}

                # Extract player name
                try:
                    name_element = row.find_element(By.CSS_SELECTOR, ".name-column a")
                    player["name"] = name_element.text.strip()
                except:
                    player["name"] = "Unknown"

                # Extract event statuses
                event_statuses = []
                event_cells = row.find_elements(By.CSS_SELECTOR, ".event-column")

                for cell in event_cells:
                    try:
                        # Check for icons (checkmark, cross, etc.)
                        icon_element = cell.find_element(By.TAG_NAME, "svg")
                        icon_class = icon_element.get_attribute("data-icon")

                        if icon_class == "check":
                            event_statuses.append("Present")
                        elif icon_class == "xmark":
                            event_statuses.append("Absent")
                        elif icon_class == "suitcase-medical":
                            event_statuses.append("Medical Leave")
                        else:
                            event_statuses.append("Unknown")
                    except:
                        event_statuses.append("Unknown")

                # Map headers to extracted data
                player["events"] = dict(zip(headers, event_statuses))

                players_data.append(player)

            return players_data

        except Exception as e:
            print(f"Error extracting table data: {e}")
            return json.dumps({"error": str(e)})

