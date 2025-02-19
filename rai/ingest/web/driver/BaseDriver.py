

from F.LOG import Log
from selenium.common import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from rai.ingest.web.driver.DriverQueue import WebBaseQueue
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

Log = Log("WebBaseDriver")


class WebBaseDriver(WebBaseQueue):
    driver: webdriver.Chrome
    options: webdriver.ChromeOptions = webdriver.ChromeOptions()

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        # self.options.add_argument("--headless")  # Run in headless mode
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--log-level=3") # se:downloadsEnabled
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)

    def get_cookies(self):
        return self.driver.get_cookies()
    def add_cookies(self, cookies):
        # Inject cookies into the new session
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        self.refresh()

    def safe_find_element(self, by, value):
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None
    def safe_find_elements(self, by, value):
        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            return None

    def quit(self): self.driver.quit()
    def back(self): self.driver.back()
    def forward(self): self.driver.forward()
    def refresh(self): self.driver.refresh()
    def wait(self): return WebDriverWait(self.driver, 10)
    def wait_body(self): WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    def safe_click(self, element) -> bool:
        try:
            element.click()
            return True
        except Exception as e:
            print(e)
            return False

    def get_credentials(self): self.driver.get_credentials()
    def add_credentials(self, credential): self.driver.add_credential(credential)
    def remove_credentials(self): self.driver.remove_all_credentials()

    def get_downloadable_files(self): return self.driver.get_downloadable_files()
    def download_file(self, file_name: str, target_directory :str): return self.driver.download_file(file_name, target_directory)
