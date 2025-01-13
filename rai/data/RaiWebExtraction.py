from F import DICT
from bs4 import BeautifulSoup
import re
from F.LOG import Log

import threading
from typing import Set, List, Optional, Dict, Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

Log = Log("RaiWebExtraction")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from rai.data import RaiPath, RaiDirectories
import time
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)

from rai.data.loaders.rai_loaders.JsonlDataLoader import JSONLDataLoader


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

class WebLoginDetails(BaseModel):
    success: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

    # If you want to store Selenium's WebElement in the model, mark them as Any
    # and allow arbitrary types via the Config class.
    user_input: Optional[Any] = None
    pass_input: Optional[Any] = None
    login_btn: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True  # Allows storing non-JSON-serializable objects


class WebPageDetails(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    content: Optional[str] = None

    # Use default_factory to get empty lists if not provided
    urls: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    # For metadata, we can store arbitrary key/value pairs
    metadata: Optional[Dict[str, Any]] = None

""" Master Web Driver """
class RaiWebDriver:
    driver: webdriver.Chrome
    options: webdriver.ChromeOptions = webdriver.ChromeOptions()
    base_url: str = ""
    do_login: bool = False
    login_details: WebLoginDetails = None
    url_details: {str:WebPageDetails} = None
    visited_urls: set[str] = set()
    all_extracted_urls: set[str] = set()
    page_urls: set[str] = set()
    page_metadata: [{}] = []
    page_images: [] = []
    page_contents: str = ""
    page_details: {str:str} = {
        'title': '',
        'author': '',
        'date': ''
    }
    irrelevant_domains = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com',
        'ads', 'adservice', 'doubleclick.net', 'tracking', 'google-analytics', 'privacy',
        'help', 'account', 'terms'
    ]

    def __init__(self, open_url: str = None):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")  # Run in headless mode
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)
        self.url_details = {}
        if open_url:

            self.open(open_url)

    def get_url_details(self, url) -> Optional[WebPageDetails]:
        return DICT.get(url, self.url_details, None)

    def create_url_details(self, url) -> Optional[WebPageDetails]:
        if not url and not DICT.get(url, self.url_details, None): return
        self.url_details[url] = WebPageDetails(
            url = url
        )
        return DICT.get(url, self.url_details, None)

    def open(self, url, wait_time=10, max_scrolls=3, username=None, password=None) -> { str:str }:
        Log.i("Opening URL:", url)
        self.create_url_details(url)
        self.base_url = RaiUrl(url)
        self.setup_login(username, password)
        login_url = RaiUrl(url).join_to_base('login')
        self.login(login_url)
        self.driver.get(url)
        self.visited_urls.add(url)
        WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.handle_popups()  # Handle any potential popups
        for _ in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Delay to ensure dynamic content is loaded

    def setup_login(self, username, password):
        if username and password:
            self.do_login = True
            self.login_details = WebLoginDetails(username=username, password=password)

    @property
    def page_title(self):
        return self.driver.title
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
        self.page_metadata = []
        self.page_metadata = meta_tags
        return meta_tags
    def handle_popups(self):
        try:
            # Example: Dismiss cookie consent popup if present
            popup_buttons = self.driver.find_elements(By.XPATH,"//button[contains(text(), 'Accept') or contains(text(), 'Agree')]")
            for button in popup_buttons:
                button.click()
                time.sleep(1)  # Allow some time for the popup to close
        except Exception as e:
            Log.e(f"Popup handling error: {str(e)}")
    def quit(self):
        self.driver.quit()
    def extract_urls(self):
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        relevant_urls = [
            link.get_attribute('href')
            for link in links
            if link.get_attribute('href') and not self.is_irrelevant_link(link.get_attribute('href'))
        ]
        self.page_urls.clear()
        self.page_urls.update(relevant_urls)
        return relevant_urls
    def extract_images(self):
        images = self.driver.find_elements(By.TAG_NAME, 'img')
        image_urls = [
            image.get_attribute('src')
            for image in images
            if image.get_attribute('src') is not None
        ]
        self.page_images = []
        self.page_images.extend(image_urls)
        return self.page_images

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
            self.page_contents = ""
            self.page_contents = self.refine_text_content(content)
            return self.page_contents
        except Exception as e:
            Log.e(f"Error extracting content: {str(e)}")
            self.page_contents = ""
            self.page_contents = self.refine_text_content(content)
            return self.page_contents
    def get_page_details(self):
        self.page_details['title'] = self.page_title
        return {
            "details": self.page_details,
            "content": self.page_contents,
            "urls": self.page_urls,
            "tags": self.page_metadata
        }
    def add_irrelevant_domains(self, *domains:str):
        for domain in domains:
            self.irrelevant_domains.extend(domain)
    def is_irrelevant_link(self, url):
        return any(domain in url for domain in self.irrelevant_domains)
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

""" Master Web Crawler """
class RaiWebExtractor(RaiWebDriver):
    scrape_limit = 0
    scrape_count = 0
    current_site_name = ""
    to_visit_urls: Set[str] = set()
    output_dir:RaiPath
    output_file:RaiPath

    def __init__(self, base_url: str, output_dir:str=None):
        super(RaiWebExtractor, self).__init__()
        if output_dir is None:
            output_dir = RaiDirectories.output()
        self.url = RaiUrl(base_url)
        self.output_dir = RaiPath(output_dir)
        self.current_site_name = self.url.site_name
        self.domain_name = self.url.savable_name
        self.output_file = RaiPath(RaiPath.join_path(self.output_dir, RaiPath.ADD_JSONL_EXT(self.domain_name)))
        self.to_visit_urls = {self.url}
        self.data_lock = threading.Lock()
        self.output_dir.verify_create_directory()
        self._load_existing_data()

    @classmethod
    def save(cls, url, page_limit:int=1):
        newcls = cls(url)
        newcls.scrape_limit = page_limit
        newcls.crawl()
        return newcls

    def _load_existing_data(self):
        self.visited_urls = JSONLDataLoader.load_file(self.output_file)

    def _save_data(self, data: dict):
        with self.data_lock: JSONLDataLoader.save_file(data, self.output_file)

    def is_within_base_url(self, url: str) -> bool:
        parsed_base = urlparse(self.url)
        parsed_url = urlparse(url)
        return parsed_url.netloc == parsed_base.netloc

    def filter_add_urls(self, new_links):
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
        # Implement your text cleaning logic here
        text = ' '.join(text.split())
        return text

    @staticmethod
    def form_data(url:str, details:dict, text:str):
        return {
            'url': url,
            'title': DICT.get('title', details, url),
            'content': text
        }

    def _scrape_page(self, url: str):
        try:
            results = self.open(url)
            text = self.clean_text(results['content'])
            details = results['details']
            self.filter_add_urls(results['urls'])
            if not text: return
            data = self.form_data(url, details, text)
            self._save_data(data)
        except (WebDriverException, TimeoutException, NoSuchElementException) as e:
            Log.e(f"Error scraping {url}: {e}")

    def crawl(self):
        while self.to_visit_urls:
            if self.scrape_limit > 0:
                if self.scrape_count >= self.scrape_limit:
                    break
            current_url = self.to_visit_urls.pop()
            if current_url in self.visited_urls:
                continue
            Log.w(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            self._scrape_page(current_url)
            self.scrape_count += 1

        # self.driver.quit()
        Log.s("Crawling completed.")

    def start(self):
        crawl_thread = threading.Thread(target=self.crawl)
        crawl_thread.start()
        crawl_thread.join()



if __name__ == '__main__':
    RaiWebExtractor.save('https://playmetrics.com/teams/194129/calendar', page_limit=1)
    # RaiWebCrawler(base_url='https://academy.veo.co', output_dir='output').start()