from assistant import openai_client
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

Log = Log("WebTools")

class WebDriver:
    driver: webdriver.Chrome
    options:webdriver.ChromeOptions = webdriver.ChromeOptions()

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")  # Run in headless mode
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)

    def open(self, url, wait_time=10, max_scrolls=3):
        self.driver.get(url)
        WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        for _ in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Delay to ensure dynamic content is loaded

    def quit(self):
        self.driver.quit()

    def extract_urls(self):
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        relevant_urls = [
            link.get_attribute('href')
            for link in links
            if link.get_attribute('href') and not is_irrelevant_link(link.get_attribute('href'))
        ]
        return relevant_urls


def selenium_get_core_page_details(url, wait_time=10, max_scrolls=3):
    # Setup WebDriver with options
    relevant_urls = []
    page_content = ''
    meta_tags = []
    core_details = {
        'title': '',
        'author': '',
        'date': ''
    }

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        Log.i(f"Opening URL: {url}")
        # Open the URL
        driver.get(url)
        # Wait until the body element is present
        WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Scroll down the page to load dynamic content if necessary
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Delay to ensure dynamic content is loaded

        # Extract page title
        core_details['title'] = driver.title

        # Extract meta tags for useful metadata like author and date
        metas = driver.find_elements(By.TAG_NAME, 'meta')
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

        # Extract page content (paragraphs and headings)
        page_content = extract_main_content(driver)
        if page_content:
            Log.s("Successfully Scrapped Web Page Contents.")
        # Find all <a> tags and extract relevant href attributes
        links = driver.find_elements(By.TAG_NAME, 'a')
        relevant_urls = [link.get_attribute('href') for link in links if
                         link.get_attribute('href') and not is_irrelevant_link(link.get_attribute('href'))]

    except TimeoutException:
        Log.e(f"Error: Timed out waiting for page to load: {url}")
    except NoSuchElementException:
        Log.e(f"Error: No body element found on the page: {url}")
    except WebDriverException as e:
        Log.e(f"WebDriver error: {str(e)}")
    finally:
        # Always close the driver
        Log.i("Closing Chrome Driver")
        driver.quit()

    # Clean the page content
    cleaned_content = refine_text_content(page_content)
    return {
        "details": core_details,
        "content": cleaned_content,
        "urls": relevant_urls,
        "tags": meta_tags
    }
def extract_main_content(driver):
    """
    Extracts the main content from the webpage by focusing on relevant tags such as
    paragraphs, headings, and main articles.
    """
    content = []
    # Extract headings (h1-h3) and paragraphs
    headings = driver.find_elements(By.XPATH, '//h1 | //h2 | //h3')
    paragraphs = driver.find_elements(By.TAG_NAME, 'p')
    for heading in headings:
        content.append(heading.text)
    for paragraph in paragraphs:
        content.append(paragraph.text)
    # Join the content into a single string
    return '\n'.join(content)
def is_irrelevant_link(url):
    """
    Returns True if the link is considered irrelevant, such as social media, advertisement, or tracking links.
    """
    irrelevant_domains = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com',
        'ads', 'adservice', 'doubleclick.net', 'tracking', 'google-analytics'
    ]
    return any(domain in url for domain in irrelevant_domains)
def remove_non_printable_ascii(text):
    """
    Remove non-printable characters from text.
    """
    return ''.join([c for c in text if ord(c) < 128])
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

""" Master Web Page Extractor """
def selenium_get_core_page_details_v2(url, wait_time=10, max_scrolls=3):
    # Setup WebDriver with options
    relevant_urls = []
    page_content = ''
    meta_tags = []
    core_details = {
        'title': '',
        'author': '',
        'date': ''
    }
    webdrive = WebDriver()
    try:
        # options = webdriver.ChromeOptions()
        # options.add_argument("--headless")  # Run in headless mode
        # options.add_argument("--disable-gpu")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--log-level=3")
        # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        print(f"Opening URL: {url}")
        webdrive.open(url)
        driver = webdrive.driver
        # # Open the URL
        # driver.get(url)
        # # Wait until the body element is present
        # WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Scroll down the page to load dynamic content if necessary
        # for _ in range(max_scrolls):
        #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        #     time.sleep(2)  # Delay to ensure dynamic content is loaded

        # Extract page title
        core_details['title'] = driver.title

        # Extract meta tags for useful metadata like author and date
        metas = driver.find_elements(By.TAG_NAME, 'meta')
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

        # Extract page content (paragraphs, headings, tables, lists, image captions)
        page_content = extract_full_content(driver)
        if page_content:
            print("Successfully Scraped Web Page Contents.")
        else:
            print("No content extracted from the page.")

        relevant_urls = webdrive.extract_urls()
        # Find all <a> tags and extract relevant href attributes
        # links = driver.find_elements(By.TAG_NAME, 'a')
        # relevant_urls = [
        #     link.get_attribute('href')
        #     for link in links
        #     if link.get_attribute('href') and not is_irrelevant_link(link.get_attribute('href'))
        # ]

    except TimeoutException:
        print(f"Error: Timed out waiting for page to load: {url}")
    except NoSuchElementException:
        print(f"Error: No body element found on the page: {url}")
    except WebDriverException as e:
        print(f"WebDriver error: {str(e)}")
    finally:
        # Always close the driver
        print("Closing Chrome Driver")
        webdrive.quit()

    # Clean the page content
    cleaned_content = refine_text_content(page_content)
    return {
        "details": core_details,
        "content": cleaned_content,
        "urls": relevant_urls,
        "tags": meta_tags
    }

def extract_full_content(driver):
    content = ''
    try:
        # Get the body of the page
        body = driver.find_element(By.TAG_NAME, 'body')
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

        # Collect text content
        for elem in text_elements:
            text = elem.get_text(separator=' ', strip=True)
            if text:
                content += text + '\n'

        return content

    except Exception as e:
        print(f"Error extracting content: {str(e)}")
        return content

""""""
def open_url(url, wait_time=10):
    try:
        # Open the URL
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode, i.e., without opening a browser window
        # driver = webdriver.Chrome(options=options)
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(url)
        # Wait until the body element is present
        WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        # Get page content
        page_content = driver.find_element(By.TAG_NAME, 'body').text
    except TimeoutException:
        print(f"Error: Timed out waiting for page to load: {url}")
        page_content = None
    except NoSuchElementException:
        print(f"Error: No body element found on the page: {url}")
        page_content = None
    finally:
        # Always close the driver
        driver.quit()
    return remove_non_printable_ascii(page_content)

def basic_get(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text()
        return page_text
    except Exception as e:
        Log.e("Request Failed.", error=e)
        return False

def extract_url_details(url: str):
    webpage_details = open_url(url)
    user_prompt = f"What is this webpage about? {webpage_details}"
    response = openai_client.chat_request("You are a helpful assistant.", user_prompt)
    print(response)
    return response

def remove_non_printable_ascii(text):
    # Define a regex pattern that matches all non-printable ASCII characters
    pattern = re.compile(r'[^\x20-\x7E\t\n\r]')
    # Substitute matched characters with an empty string
    cleaned_text = re.sub(pattern, '', text)
    return (cleaned_text
            .replace("\t", "")
            .replace("\r", "")
            .replace("\n\n", "\n")
            )

def remove_non_printable_ascii(text):
    # Filter out non-printable ASCII characters
    return ''.join(c for c in text if 32 <= ord(c) <= 126 or c in '\n\r\t')


if __name__ == "__main__":
    result = selenium_get_core_page_details_v2("https://www.parkcitysoccer.org/staff")
    print(result)