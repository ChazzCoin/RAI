from assistant import openai_client
from bs4 import BeautifulSoup
import requests, re
from F.LOG import Log
Log = Log("WebTools")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time

def selenium_get_with_urls(url, wait_time=10):
    # Setup WebDriver with options

    all_urls = []

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode, i.e., without opening a browser window
        # driver = webdriver.Chrome(options=options)
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        # Open the URL
        driver.get(url)
        time.sleep(wait_time)
        # Wait until the body element is present
        WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        # Find all <a> tags and extract href attributes
        links = driver.find_elements(By.TAG_NAME, 'a')
        all_urls = [link.get_attribute('href') for link in links if link.get_attribute('href')]
        page_content = driver.find_element(By.TAG_NAME, 'body').text
    except TimeoutException:
        print(f"Error: Timed out waiting for page to load: {url}")
    except NoSuchElementException:
        print(f"Error: No body element found on the page: {url}")
    finally:
        # Always close the driver
        driver.quit()
    return {
        "content": remove_non_printable_ascii(page_content),
        "urls": all_urls
    }

def remove_non_printable_ascii(text):
    # Filter out non-printable ASCII characters
    return ''.join(c for c in text if 32 <= ord(c) <= 126 or c in '\n\r\t')

def selenium_get_with_urls_v2(url, wait_time=10, max_scrolls=3):
    # Setup WebDriver with options
    all_urls = []
    page_content = ''
    meta_tags = []
    image_urls = []
    script_urls = []
    css_urls = []

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        # Open the URL
        driver.get(url)

        # Wait until the body element is present
        WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Scroll down the page to load dynamic content if any
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)  # Slight delay to ensure content is loaded

        # Extract page content
        page_content = driver.find_element(By.TAG_NAME, 'body').text

        # Find all <a> tags and extract href attributes
        links = driver.find_elements(By.TAG_NAME, 'a')
        all_urls = [link.get_attribute('href') for link in links if link.get_attribute('href')]

        # Extract meta tags
        metas = driver.find_elements(By.TAG_NAME, 'meta')
        for meta in metas:
            name = meta.get_attribute('name')
            content = meta.get_attribute('content')
            if name and content:
                meta_tags.append({name: content})

        # Extract images
        images = driver.find_elements(By.TAG_NAME, 'img')
        image_urls = [img.get_attribute('src') for img in images if img.get_attribute('src')]

        # Extract scripts
        scripts = driver.find_elements(By.TAG_NAME, 'script')
        script_urls = [script.get_attribute('src') for script in scripts if script.get_attribute('src')]

        # Extract stylesheets (CSS)
        stylesheets = driver.find_elements(By.TAG_NAME, 'link')
        css_urls = [sheet.get_attribute('href') for sheet in stylesheets if sheet.get_attribute('rel') == 'stylesheet']

    except TimeoutException:
        print(f"Error: Timed out waiting for page to load: {url}")
    except NoSuchElementException:
        print(f"Error: No body element found on the page: {url}")
    except WebDriverException as e:
        print(f"WebDriver error: {str(e)}")
    finally:
        # Always close the driver
        driver.quit()

    # Clean page content of non-printable characters
    cleaned_content = remove_non_printable_ascii(page_content)

    return {
        "page_content": cleaned_content,
        "all_urls": all_urls,
        "meta_tags": meta_tags,
        "image_urls": image_urls,
        "script_urls": script_urls,
        "css_urls": css_urls
    }

""" Master Web Page Extractor """
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

if __name__ == "__main__":
    from dataset.formatters.auto_format import request_auto_format_of_raw_data
    from files.save import DataSaver
    # result = selenium_get_with_urls("https://nucschallengerfall2024.sportsaffinity.com/tour/public/info/schedule_results2.asp?sessionguid=&flightguid=799ED838-B764-407B-B753-9CF219F6D04F&tournamentguid=6A54E093-43C7-4CA7-A52D-7B255A0B0659")
    # auto_formatted = request_auto_format_of_raw_data(str(result))
    # print(auto_formatted)
    # DataSaver.save_txt(auto_formatted, "auto_formatted_schedule")
    result = selenium_get_core_page_details("https://scholar.barrowneuro.org/neuropsychology/237/")
    print(result)