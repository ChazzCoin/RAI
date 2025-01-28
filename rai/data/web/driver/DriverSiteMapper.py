import time
from F import DICT, LIST
from F.LOG import Log
from rai.data.web.WebModels import SiteExtractDetails
from rai.data.web.driver.WebDriver import RaiWebDriver

from urllib.parse import urlparse
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    NoSuchElementException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

Log = Log("RaiWebPageScrape")
""" Master Web Driver """
class RaiWebSiteMapper(RaiWebDriver):
    site = None
    site_title = ""
    page_count = 0
    found_tables = []

    def site_recon(self, url: str, username=None, password=None):
        self.open(url, username, password)
        Log.i("Extracting Site Details.")
        return self.gather_site()

    def _gather_clickable_elements(self):
        links = self.driver.find_elements(By.TAG_NAME, "a")
        btns = self.driver.find_elements(By.TAG_NAME, "button")
        return links + btns  # union (no dedup needed for iteration)

    def _try_click_and_capture(self, element, current_url):
        try:
            element.click()
            time.sleep(2)  # let the browser load the new page

            new_url = self.driver.current_url
            if new_url != current_url:
                self.add_update_recon_queue(new_url)

        except (StaleElementReferenceException, ElementClickInterceptedException,
                NoSuchElementException, WebDriverException) as e:
            print(f"Click failed for element. Reason: {e}")

        try:
            if self.driver.current_url != current_url:
                self.driver.get(current_url)
                time.sleep(1)
        except WebDriverException as e:
            print(f"Navigation back to {current_url} failed. Reason: {e}")
    def gather_site(self):
        start_url = self.driver.current_url
        self.site_title = self.driver.title
        parsed_url = urlparse(start_url)
        self.start_domain = parsed_url.netloc
        self.to_visit_urls.clear()
        self.recon_queue.clear()

        self.to_visit_urls.add(start_url)
        self.recon_queue.append(start_url)

        while self.recon_queue:
            current_url = self.recon_queue.popleft()
            self.page_count = self.page_count + 1
            print(f"Processing: {current_url}")

            # Navigate to the page (if not already on it)
            if self.driver.current_url != current_url:
                try:
                    self.driver.get(current_url)
                    self.wait().until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                except TimeoutException:
                    print(f"Timeout loading {current_url}, skipping...")
                    continue

            rows_data = self.deep_table_extraction()
            if rows_data:
                self.found_tables.extend(rows_data)
                for row in rows_data:
                    row_urls = DICT.get("Urls", row, None)
                    if row_urls:
                        for url in row_urls:
                            self.add_update_recon_queue(url)
                    row_url = DICT.get("Url", row, None)
                    if row_url:
                        self.add_update_recon_queue(row_url)
            if self.driver.current_url != current_url:
                try:
                    self.driver.get(current_url)
                    self.wait().until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                except TimeoutException:
                    print(f"Timeout loading {current_url}, skipping...")
                    continue
            # Gather the clickable elements on the page
            clickable_elements = self._gather_clickable_elements()
            for i in range(len(clickable_elements)):
                # Re-locate all clickable elements on the page
                # (previous references are invalid if we navigated away)
                fresh_clickables = self._gather_clickable_elements()
                if i >= len(fresh_clickables):
                    break  # safeguard if the count changed

                self._try_click_and_capture(fresh_clickables[i], current_url)
        self.site = SiteExtractDetails(
            title=self.site_title,
            base_url=self.start_domain,
            page_count=str(self.page_count),
            tables=self.found_tables,
            metadata={},
            urls=list(self.to_visit_urls)
        )
        return self.site
    def deep_table_extraction(self, table_selector: str = "table") -> [{}]:
        all_rows_with_urls = []  # Final list to return
        max_pages = 20  # Safety limit to avoid infinite loops
        page_count = 0
        try:
            """ Loop Through Each Page of the Table """
            while True:
                if page_count >= max_pages: break

                attempts = [
                    f"{table_selector} tr.clickable",
                    f"{table_selector} tr"
                ]
                selector = f"{table_selector} tr.clickable"
                for attempt in attempts:
                    try:
                        clickable_rows = self.driver.find_elements(By.CSS_SELECTOR, attempt)
                        if clickable_rows:
                            selector = attempt
                            break
                    except Exception:
                        continue

                self.wait().until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )

                table_data = self.extract_page_table()  # returns a list of row dicts
                clickable_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                row_element = None
                row_links = None
                row_count = min(len(clickable_rows), len(table_data))

                for index in range(row_count):
                    print("Page:", page_count)
                    print("Row:", index)
                    try:
                        clickable_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if index >= len(clickable_rows):
                            break

                        row_dict = table_data[index]
                        row_element = clickable_rows[index]
                        row_urls = []
                        try:
                            temp_url = self.driver.current_url
                            self.driver.execute_script(
                                "arguments[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));",
                                row_element
                            )
                            time.sleep(2)
                            if str(temp_url) != str(self.driver.current_url):
                                row_dict["Url"] = self.driver.current_url
                                row_urls.append(self.driver.current_url)
                                self.driver.get(temp_url)
                                if page_count > 0:
                                    time.sleep(2)
                                    self.click_next_table_page(page_count)
                                time.sleep(2)
                                self.wait().until(EC.presence_of_all_elements_located((By.TAG_NAME, 'body')))
                                clickable_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                row_element = clickable_rows[index]
                        except Exception as e:
                            print(e)

                        # Attempt to extract links inside the row
                        row_links = row_element.find_elements(By.TAG_NAME, "a")
                        if row_links:
                            keep_max = len(row_links)
                            keep_index = -1
                            keep_going = True
                            while keep_going:
                                if keep_index >= keep_max: break
                                keep_index = keep_index + 1
                                try:
                                    # self.driver.execute_script("arguments[0].click();", link)
                                    self.driver.execute_script(
                                        "arguments[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));",
                                        row_links[keep_index]
                                    )

                                    time.sleep(2)  # Wait for potential UI change
                                    temp_url = self.driver.current_url
                                    if str(temp_url) == str(self.driver.current_url):
                                        try:
                                            modal_selector = "div.modal, div.full-screen-modal, div.responses-modal-body, div.modal-card-body"
                                            self.wait().until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
                                            )

                                            modal_element = self.driver.find_element(By.CSS_SELECTOR,
                                                                                            modal_selector)
                                            modal_content = modal_element.text
                                            row_dict["ModalContent"] = modal_content
                                            self.driver.refresh()
                                            self.wait().until(
                                                EC.presence_of_all_elements_located(
                                                    (By.CSS_SELECTOR, selector)
                                                ))
                                            if page_count > 0:
                                                self.click_next_table_page(page_count)
                                        except Exception as e:
                                            print(e)
                                            continue
                                    else:
                                        row_urls.append(temp_url)
                                        self.driver.back()
                                        self.wait().until(
                                            EC.presence_of_all_elements_located(
                                                (By.CSS_SELECTOR, selector)
                                            ))
                                    clickable_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    row_element = clickable_rows[index]
                                    row_links = row_element.find_elements(By.TAG_NAME, "a")
                                except Exception as e:
                                    print(e)
                            row_dict["Urls"] = row_urls
                        all_rows_with_urls.append(row_dict)
                    except Exception as e:
                        print(f"Overall handling error: {e}")
                        all_rows_with_urls.append(row_dict)
                        continue
                page_count = page_count + 1
                if not self.click_next_table_page(1): break
                time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
        return all_rows_with_urls

if __name__ == '__main__':
    email = "jperson@parkcitysoccer.org"
    password = "Philly23!"
    RaiWebSiteMapper().site_recon(url="https://playmetrics.com/club-admin/teams", username=email, password=password)