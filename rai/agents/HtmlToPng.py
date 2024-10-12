from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import time

def set_location(driver, latitude, longitude, accuracy):
    # Using Chrome DevTools Protocol to set geolocation
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy
    }
    driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)

def html_to_png(url, output_file='output.png', width=1200, height=2340, wait_for_element=None):
    # Setup Selenium with headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={width},{height}")

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    set_location(driver, 33.2443, -86.8164, 100)
    try:

        # Load the webpage
        print("Opening URL..")
        driver.get(url)

        # Wait for a specific element to load if provided (useful for pages with dynamic content)
        if wait_for_element:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
            )
            time.sleep(5)
        else:
            # Otherwise, wait for the whole page to load
            print("Waiting for page to load...")
            time.sleep(10)  # Adjust this time as needed

        # Take a screenshot and save it as a PNG file
        print("Taking Screenshot...")
        driver.save_screenshot(output_file)

        # Optionally, crop the image to the content's actual size
        img = Image.open(output_file)
        img = img.crop(img.getbbox())
        img.save(output_file)

        print(f"Screenshot saved as {output_file}")

    finally:
        # Close the WebDriver session
        driver.quit()

# Example usage
if __name__ == "__main__":
    html_to_png("https://news.google.com/home?hl=en-US&gl=US&ceid=US:en", "/Users/chazzromeo/ChazzCoin/MedRefs/files/images/suspended.png", wait_for_element="body")
