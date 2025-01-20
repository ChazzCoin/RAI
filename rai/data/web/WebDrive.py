from io import BytesIO
from urllib.parse import urlparse
# import PyPDF2
from rai.data.parsers.Pdf import FPDF
import pytesseract
import requests
from F import DICT, LIST
from bs4 import BeautifulSoup
import re
from F.LOG import Log

from typing import Optional, List, Dict, Any, Set
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.common.exceptions import (
    NoSuchElementException,
)

from rai.data.utilities.TextUtils import TextProcessor
from rai.data.web.WebModels import SeleniumLocator, ButtonModel, InputFieldModel, WebLoginDetails, PageExtractDetails
Log = Log("WebMaster")

def remove_non_printable_ascii(text):
    """
    Remove non-printable characters from text.
    """
    return ''.join([c for c in text if ord(c) < 128])

class RaiUrl(str):
    url: str = ""
    url_obj = None

    def __init__(self, url:str):
        self.url = url
        self.url_obj = urlparse(url)

    def __new__(cls, url):
        # `__new__` is used to create the actual instance since str is immutable
        return super(RaiUrl, cls).__new__(cls, url)
    @property
    def site_name(self):
        return self.url_obj.netloc
    @property
    def savable_name(self, replace_with:str='_'):
        return self.url_obj.netloc.replace('.', replace_with)
    @property
    def path(self):
        return self.url_obj.path  # /some/path
    @property
    def scheme(self):
        return self.url_obj.scheme  # https
    def join_to_base(self, ext):
        return f"{self.url_obj.scheme}://{self.url_obj.netloc}/{ext}"


class WebBaseHelper(TextProcessor):

    @staticmethod
    def clean_text(text: str) -> str:
        text = remove_non_printable_ascii(text)
        return ' '.join(text.split())

    @staticmethod
    def is_within_base_url(base_url, candidate_url: str) -> bool:
        parsed_base = urlparse(str(base_url))  # ensure string
        parsed_candidate = urlparse(candidate_url)
        return parsed_candidate.netloc == parsed_base.netloc

    @staticmethod
    def refine_text_content(content):
        """
        Remove unnecessary sections like footers, social media links, copyrights, and clean the text content.
        """
        # Define some patterns for sections to be ignored
        unwanted_patterns = [
            r'(\s|^)Social Media\s?.*',  # Matches "Social Media" and the text after
            r'(\s|^)Copyright.*',  # Matches "Copyright" and the text after
            r'(\s|^)Follow us.*',  # Matches "Follow us" sections
            r'(\s|^)Share.*',  # Matches "Share" links/buttons
            r'(\s|^)Subscribe.*',  # Matches "Subscribe" sections
            r'(\s|^)Cookie.*',  # Matches "Cookie" banners
            r'(\s|^)Terms of.*',  # Matches "Terms of" sections
            r'(\s|^)Privacy Policy.*',  # Matches "Privacy Policy" sections
            r'(\s|^)Related Articles.*',  # Matches "Related Articles" sections
        ]
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        # Optionally remove non-printable characters or extra white spaces
        content = remove_non_printable_ascii(content)
        content = re.sub(r'\s+', ' ', content).strip()  # Normalize white space

        return content


class WebBaseQueue(WebBaseHelper):
    all_extracted_urls: set[str] = set()
    to_visit_urls: Set[str] = set()
    visited_urls: Set[str] = set()
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

    def add_urls_to_queue(self, new_links: List[str]):
        filtered_links = []
        for link in new_links:
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



class WebBaseDriver(WebBaseQueue):
    driver: webdriver.Chrome
    options: webdriver.ChromeOptions = webdriver.ChromeOptions()

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")  # Run in headless mode
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)

    def quit(self): self.driver.quit()


class WebBaseExtract(WebBaseDriver):
    @property
    def page_title(self): return self.driver.title
    """ URLS """
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
        """
        Finds and extracts every single image URL from the page.

        It searches for:
          1. <img> tags (including lazy-loaded images via data-src).
          2. Inline CSS that contains background images.
          3. <picture> elements with <source> tags using srcset attributes.

        Returns:
            A list of unique image URLs.
        """
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
    """ TABLES """
    def extract_all_tables(self):
        # 1. Find all tables in the DOM
        table_elements = self.driver.find_elements(By.TAG_NAME, "table")

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
    def extract_content(self):
        content = ''
        try:
            # Get the body of the page
            body = self.driver.find_element(By.TAG_NAME, 'body')
            # Get the innerHTML of the body
            html = body.get_attribute('innerHTML')
            # Parse the HTML using BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            # Extract text from paragraphs and headings
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            # Extract text from tables
            tables = soup.find_all('table')
            for table in tables:
                text_elements.extend(table.find_all(['caption', 'td', 'th']))
            # Extract captions from images (for photo galleries)
            images = soup.find_all('img')
            for img in images:
                alt_text = img.get('alt')
                title_text = img.get('title')
                if alt_text:
                    content += alt_text + '\n'
                elif title_text:
                    content += title_text + '\n'
            # Extract text from lists
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                text_elements.extend(lst.find_all('li'))
            # Extract text from other common popups or modals
            modals = soup.find_all('div', {'class': lambda x: x and ('popup' in x or 'modal' in x)})
            for modal in modals:
                modal_text = modal.get_text(separator=' ', strip=True)
                if modal_text:
                    content += modal_text + '\n'
            # Collect text content
            for elem in text_elements:
                text = elem.get_text(separator=' ', strip=True)
                if text:
                    content += text + '\n'
            return self.refine_text_content(content)
        except Exception as e:
            Log.e(f"Error extracting content: {str(e)}")
            return self.refine_text_content(content)
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

class WebBaseActions(WebBaseExtract):
    do_login: bool = False
    max_scrolls = 5
    """ Future Pipeline Driver """
    def _find_element_by_locator(self, locator: SeleniumLocator):
        if locator.element_id:
            return self.driver.find_element(By.ID, locator.element_id)
        elif locator.name:
            return self.driver.find_element(By.NAME, locator.name)
        elif locator.css_selector:
            return self.driver.find_element(By.CSS_SELECTOR, locator.css_selector)
        else:
            return self.driver.find_element(By.TAG_NAME, locator.tag_name)
    def click_button(self, button_model):
        css_sel = button_model.locator.css_selector
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        element.click()
    def fill_input_field(self, input_model, value: str):
        css_sel = input_model.locator.css_selector
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        element.clear()
        element.send_keys(value)
    def fill_textarea(self, textarea_model, value: str):
        css_sel = textarea_model.locator.css_selector
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        element.clear()
        element.send_keys(value)
    def select_dropdown_option(self, select_model, visible_text: str):
        css_sel = select_model.locator.css_selector
        select_element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        dropdown = Select(select_element)
        dropdown.select_by_visible_text(visible_text)
    """ LOGIN """
    def setup_login(self, username, password):
        if username and password:
            self.do_login = True
            self.login_details = WebLoginDetails(username=username, password=password)
    def login(self, url: str):
        if not self.do_login: return
        self.driver.get(url)
        time.sleep(3)
        # Initialize placeholders
        username_element = None
        password_element = None
        login_button_element = None

        try:
            # 1. Find candidate for username
            #    Common practices: type="text" or type="email", name/id that contains "user"/"email"/"login"
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in all_inputs:
                input_type = inp.get_attribute("type") or ""
                name_attr = (inp.get_attribute("name") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                placeholder_attr = (inp.get_attribute("placeholder") or "").lower()

                # Try to detect a username or email field:
                # If type is text or email, and if the name/id/placeholder suggests "user" or "email"
                if (
                        (input_type in ["text", "email"]) and
                        ("user" in name_attr or "user" in id_attr or "email" in name_attr or "email" in id_attr or
                         "user" in placeholder_attr or "email" in placeholder_attr)
                ):
                    username_element = inp
                    break
            time.sleep(2)
            # 2. Find candidate for password
            for inp in all_inputs:
                input_type = inp.get_attribute("type") or ""
                if input_type == "password":
                    password_element = inp
                    break

            # 3. Find candidate for Login/Sign-In button
            #    We look for <button> or <input type="submit"> or <input type="button">
            #    containing "Login" or "Sign In" in text/value attributes
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            all_inputs += self.driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']")
            time.sleep(2)
            # Combine both sets of possible button candidates
            for btn in all_buttons + all_inputs:
                btn_text = (btn.text or "").strip().lower()
                btn_value = (btn.get_attribute("value") or "").strip().lower()

                if any(keyword in btn_text for keyword in ["login", "log in", "sign in", "signin"]):
                    login_button_element = btn
                    break
                if any(keyword in btn_value for keyword in ["login", "log in", "sign in", "signin"]):
                    login_button_element = btn
                    break
        except NoSuchElementException:
            Log.e("Some element(s) could not be found on the page.")

        if self.login_details:
            self.login_details.user_input = username_element
            self.login_details.pass_input = password_element
            self.login_details.login_btn = login_button_element
        else:
            self.login_details = WebLoginDetails(
                user_input=username_element,
                pass_input=password_element,
                login_btn=login_button_element,
            )

        if username_element and password_element and login_button_element:
            self.login_details.success = True
            self.perform_login()
    def perform_login(self):
        Log.i("Logging In...")
        if not self.login_details or not self.login_details.success:
            return
        time.sleep(1)
        if self.login_details.user_input and self.login_details.pass_input and self.login_details.login_btn:
            # Type the username and password
            self.login_details.user_input.clear()  # Clear any existing text (optional)
            self.login_details.user_input.send_keys(self.login_details.username)
            time.sleep(1)
            self.login_details.pass_input.clear()
            self.login_details.pass_input.send_keys(self.login_details.password)
            time.sleep(1)
            # Click the login/sign-in button
            self.login_details.login_btn.click()
            time.sleep(2)
            Log.s("Logged In!")
        else:
            print("Error: One or more login elements were not found or are invalid.")
            Log.e("FAILED to Log In!")
    """ HELPERS """
    def handle_popups(self):
        try:
            # Example: Dismiss cookie consent popup if present
            popup_buttons = self.driver.find_elements(By.XPATH,"//button[contains(text(), 'Accept') or contains(text(), 'Agree')]")
            for button in popup_buttons:
                button.click()
                time.sleep(1)  # Allow some time for the popup to close
        except Exception as e:
            Log.e(f"Popup handling error: {str(e)}")
    def do_infinite_scroll(self):
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Delay to ensure dynamic content is loaded



""" Master Web Driver """
class RaiWebDriver(WebBaseActions):
    base_url: str = ""

    def __init__(self, open_url: str = None):
        super().__init__()
        if open_url: self.open(open_url)

    def open(self, url, wait_time=10, username=None, password=None, max_scrolls=5) -> { str:str }:
        Log.i("Opening URL:", url)
        self.base_url = RaiUrl(url)
        self.max_scrolls = max_scrolls
        self.setup_login(username, password)
        login_url = RaiUrl(url).join_to_base('login')
        self.login(login_url)
        self.driver.get(url)
        self.visited_urls.add(url)
        WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.handle_popups()  # Handle any potential popups
        time.sleep(2)


