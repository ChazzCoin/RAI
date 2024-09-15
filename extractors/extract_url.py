from assistant import openai_client
from bs4 import BeautifulSoup
import requests, re
from F.LOG import Log
Log = Log("FWEB.Core.HttpRequest")
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
    return remove_non_printable_ascii(page_content), all_urls

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
    result = selenium_get_with_urls("https://nucschallengerfall2024.sportsaffinity.com/tour/public/info/schedule_results2.asp?sessionguid=&flightguid=799ED838-B764-407B-B753-9CF219F6D04F&tournamentguid=6A54E093-43C7-4CA7-A52D-7B255A0B0659")
    auto_formatted = request_auto_format_of_raw_data(str(result))
    print(auto_formatted)
    DataSaver.save_txt(auto_formatted, "auto_formatted_schedule")