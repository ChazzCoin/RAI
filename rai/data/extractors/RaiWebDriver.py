from selenium.webdriver.remote.webelement import WebElement

from rai.assistant import openai_client
from bs4 import BeautifulSoup
import requests, re
from F.LOG import Log
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time

class RaiWebDriver:
    driver: webdriver.Chrome
    options: webdriver.ChromeOptions = webdriver.ChromeOptions()
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
        'ads', 'adservice', 'doubleclick.net', 'tracking', 'google-analytics'
    ]

    def __init__(self, open_url:str=None):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")  # Run in headless mode
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)
        if open_url:
            self.open(open_url)

    def open(self, url, wait_time=10, max_scrolls=3) -> { str:str }:
        self.driver.get(url)
        self.visited_urls.add(url)
        WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.handle_popups()  # Handle any potential popups
        for _ in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Delay to ensure dynamic content is loaded
        self.extract_urls()
        self.extract_metadata()
        self.extract_images()
        self.extract_content()
        return self.get_page_details()

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
    def add_irrelevant_domains(self, *domains:str):
        for domain in domains:
            self.irrelevant_domains.extend(domain)
    def is_irrelevant_link(self, url):
        return any(domain in url for domain in self.irrelevant_domains)


def remove_non_printable_ascii(text):
    """
    Remove non-printable characters from text.
    """
    return ''.join([c for c in text if ord(c) < 128])