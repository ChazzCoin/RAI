import time
from typing import Optional
import re
from FNLP.Regex import Re
from F import DICT, LIST
from F.LOG import Log
from selenium.common import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from rai.composers.TextAnalysisAgent import TextAnalysisAgent
from rai.data.loaders.rai_loaders.BaseLoad import RaiDocCreator
from rai.data.web.WebModels import PageExtractDetails
from rai.data.web.driver.DriverExtractor import WebBaseExtract
from rai.data.web.RaiUrl import RaiUrl
from selenium.webdriver.support import expected_conditions as EC

from rai.data.web.soup.BodyExtractor import WebBodyExtractor
from rai.data.web.soup.UrlExtractor import WebUrlExtractor
from rai.data.web.soup.WebExtractor import WebActionExtractor

from bs4 import BeautifulSoup

Log = Log("RaiWebPageScrape")
""" Master Web Driver """
class RaiWebPageScrape(WebBaseExtract, RaiDocCreator):

    def __init__(self, open_url: str = None, username=None, password=None):
        super().__init__()
        if open_url: self.open(open_url, username, password)

    @classmethod
    def new(cls): return cls()

    def open(self, url, username=None, password=None) -> { str:str }:
        Log.i("Opening URL:", url)
        self.base_url = RaiUrl(url)
        self.login(username, password)
        self.driver.get(url)
        self.visited_urls.add(url)
        self.wait().until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.parse(self.driver.page_source)
        time.sleep(2)

    def scrape_light(self, url: str, username=None, password=None):
        self.open(url, username, password)
        Log.i("Extracting Page.")
        # pdf_urls = self.extract_pdf_urls()
        # img_urls = self.extract_image_urls()
        # image_texts = self.extract_text_from_image_urls(img_urls)
        # metadata = self.extract_metadata()
        # body = WebBodyExtractor.pipeline(self.driver.page_source)
        # actions = WebActionExtractor.pipeline(self.driver.page_source)
        # content = self.extract_content()
        # lists = self.extract_lists()
        # urls1 = self.extract_urls()
        # urls2 = WebUrlExtractor.pipeline(self.driver.page_source, base_url=self.base_url)
        tables = self.extract_all_tables()
        data = self.extract_row_data()
        dataUrls = [dat['Url'] for dat in data]
        # data1 = self.extract_clickable_row_links1()
        calendar_events = self._extract_calendar_events()
        table_events = self._extract_table_events()
        print("Done.")

    def scrape_page(self, url: str) -> Optional[PageExtractDetails]:
        try:
            self.open(url)
            Log.i("Extracting Page.")

            data = self.extract_all_clickable_elements(max_clicks=50)

            """ Extract All Table Data """
            table_data = self.extract_clickable_row_links()

            """ Extract PDF Files """
            pdfs = self.extract_pdf_urls()
            pdf_texts = self.extract_text_from_pdf_urls(pdfs)

            """ Extract Images """
            images = self.extract_image_urls()
            image_texts = self.extract_text_from_image_urls(images)

            """ Extract Events """
            events_1 = self.extract_events()

            """ Extract Urls """
            urls = WebUrlExtractor.pipeline(self.driver.page_source, base_url=self.base_url)
            urls2 = self.extract_urls()
            """ Extract Actions """
            actions = WebActionExtractor.pipeline(self.driver.page_source)

            """ Extract Body """
            body = WebBodyExtractor.pipeline(self.driver.page_source)

            final_content = f"{body.combined_text}\n\n{' '.join(image_texts)}"
            print(final_content)

            """ Add New Urls to Queue """
            self.add_urls_to_queue(LIST.merge_lists(urls, urls2))

            """ Page Extraction Model """
            page = TextAnalysisAgent.analyze_text_async(
                content=body.combined_text,
                url=self.current_url,
                page_title=self.page_title
            )
            page.title = self.page_title
            page.url = url
            page.author = "RaiWebPageScrape"
            page.events = LIST.merge_lists(page.events, events_1)
            page.body = body
            page.actions = actions
            page.images = images
            page.images_content = image_texts
            page.pdfs = pdfs
            page.pdfs_content = pdf_texts
            page.tables = table_data

            self.pages.append(page)
            self.to_documents(page)
            Log.s(f"Successfully Scraped Page: {url}")
            return page
        except (WebDriverException, TimeoutException, NoSuchElementException) as e:
            Log.e(f"Error Scraping {url}: {e}")
            return None
    def extract_all_clickable_elements(self, max_clicks: int = 50) -> [{}]:
        """
        Scans the current page in Selenium for all 'clickable' elements,
        attempts to click each to gather destination URL and additional content.

        Returns a list of dictionaries. Each dict contains:
          - 'tag_name': str
          - 'text': str
          - 'attributes': dict of element's attributes
          - 'locator': a CSS or XPath you can reuse if needed
          - 'clicked_url': str (the URL after clicking)
          - 'post_click_info': any data extracted from the new page (e.g., title)
        And anything else you’d like to attach.

        :param driver: An active Selenium WebDriver (pointing to a loaded page).
        :param max_clicks: Safety limit on how many elements to click (avoid huge or infinite loops).
        """
        tempDriver = RaiWebPageScrape()
        tempDriver.open(url=self.driver.current_url)
        time.sleep(2)
        clickable_candidates: [WebElement] = []

        # a) All anchor tags <a>
        anchors = tempDriver.driver.find_elements(By.TAG_NAME, "a")
        clickable_candidates.extend(anchors)

        # b) All button tags <button>
        buttons = tempDriver.driver.find_elements(By.TAG_NAME, "button")
        clickable_candidates.extend(buttons)

        # c) Inputs that could be clickable
        inputs = tempDriver.driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit' or @type='image']")
        clickable_candidates.extend(inputs)

        # d) Elements with an 'onclick' attribute
        onclick_elems = tempDriver.driver.find_elements(By.XPATH, "//*[@onclick]")
        clickable_candidates.extend(onclick_elems)

        # e) Elements with role="button" or role="link"
        role_btn_link = tempDriver.driver.find_elements(By.XPATH, "//*[@role='button' or @role='link']")
        clickable_candidates.extend(role_btn_link)

        # Convert to a list of unique webelements by id
        # (In Selenium, the same element can appear multiple times if found by different queries.)
        unique_set = set(clickable_candidates)
        clickable_candidates = list(unique_set)

        # We’ll store final data here
        results = []
        urls = []
        candidate_data = []
        for elem in clickable_candidates:
            try:
                elem.click()
                time.sleep(2)
                url = tempDriver.driver.current_url
                urls.append(url)
                candidate_data.append(elem)
                tempDriver.back()
            except Exception as e:
                print(e)
                continue

        # 3) Now loop over our stored candidate_data, re-locate each by XPATH, then click & gather info
        clicks_performed = 0
        for data in candidate_data:
            if clicks_performed >= max_clicks:
                break
            try:
                xpath = data["xpath"]
                # Re-locate the element
                try:
                    target = tempDriver.driver.find_element(By.XPATH, xpath)
                except NoSuchElementException:
                    # Possibly the DOM changed
                    continue

                # If the element is not displayed or is behind an overlay, consider scrolling or JS click
                try:
                    # Scroll into view
                    tempDriver.driver.execute_script("arguments[0].scrollIntoView(true);", target)
                    time.sleep(0.5)

                    # Attempt a normal click
                    target.click()
                except (ElementClickInterceptedException, StaleElementReferenceException):
                    # Fallback: do a JavaScript click
                    tempDriver.driver.execute_script("arguments[0].click();", target)

                time.sleep(1)  # Wait for potential navigation or page change

                # Build the final record
                record = {
                    "tag_name": data["tag_name"],
                    "text": data["text"],
                    "attributes": data["attributes"],
                    "locator": data["xpath"],
                    "clicked_url": tempDriver.driver.current_url,  # The URL after clicking
                    # You can extract more content from the new page if desired:
                    "post_click_info": {
                        "title": tempDriver.driver.title,
                        # For instance, you could store a snippet of page_source or some specific elements:
                        # "page_source_snippet": driver.page_source[:500]
                    }
                }
                results.append(record)
                clicks_performed += 1

                # If it’s a real navigation, we might want to go back
                # (If the page changed, going back ensures we can keep clicking the next item.)
                # If some "clickable" just opened a modal or performed an ajax refresh, adapt accordingly.
                tempDriver.driver.back()

                # Wait for the old DOM to reappear
                time.sleep(1)
            except Exception as e:
                print(e)
                clicks_performed += 1
                continue
        return results

    def extract_row_data(self, table_selector: str = "table") -> [{}]:
        tableDriver = self.new()
        tableDriver.add_cookies(self.get_cookies())
        all_rows_with_urls = []  # Final list to return
        max_pages = 20  # Safety limit to avoid infinite loops
        page_count = 0

        try:
            # 1) Load the page
            tableDriver.open(
                url=self.driver.current_url,
                username=self.login_details.username,
                password=self.login_details.password,
            )

            while True:
                if page_count >= max_pages:
                    break

                attempts = [
                    f"{table_selector} tr.clickable",
                    f"{table_selector} tr"
                ]
                selector = f"{table_selector} tr.clickable"
                for attempt in attempts:
                    try:
                        clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, attempt)
                        if clickable_rows:
                            selector = attempt
                            break
                    except Exception:
                        continue

                tableDriver.wait().until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )

                table_data = tableDriver.extract_all_tables()  # returns a list of row dicts
                clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, selector)
                row_element = None
                row_links = None
                row_count = min(len(clickable_rows), len(table_data))

                for index in range(row_count):
                    try:
                        clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, selector)
                        if index >= len(clickable_rows):
                            break

                        row_dict = table_data[index]
                        row_element = clickable_rows[index]

                        # Attempt to extract links inside the row
                        row_links = row_element.find_elements(By.TAG_NAME, "a")
                        row_urls = []
                        row_modals = []
                        has_modals = False
                        if row_links:
                            keep_max = len(row_links)
                            keep_index = -1
                            keep_going = True
                            while keep_going:
                                if keep_index >= keep_max: break
                                keep_index = keep_index + 1
                                try:
                                    # tableDriver.driver.execute_script("arguments[0].click();", link)
                                    tableDriver.driver.execute_script(
                                        "arguments[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));",
                                        row_links[keep_index]
                                    )

                                    time.sleep(2)  # Wait for potential UI change
                                    temp_url = tableDriver.driver.current_url
                                    if str(temp_url) == str(self.driver.current_url):
                                        try:

                                            # modal_elements = tableDriver.driver.find_elements(By.TAG_NAME, 'div')
                                            # found_modal = None
                                            # stop_search = False
                                            # while not stop_search:
                                            #     for div in modal_elements:
                                            #         if stop_search: break
                                            #         str_div = str(div.get_attribute("class"))
                                            #         str_tag = str(div.get_attribute("tag_name"))
                                            #         if Re.contains("modal", str_div):
                                            #             if Re.contains_any(["body", "full-screen"], str_div):
                                            #                 found_modal = div
                                            #                 stop_search = True
                                            #                 break
                                            #         continue

                                            modal_selector = "div.modal, div.full-screen-modal, div.responses-modal-body, div.modal-card-body"
                                            tableDriver.wait().until(
                                                EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
                                            )

                                            modal_element = tableDriver.driver.find_element(By.CSS_SELECTOR,
                                                                                            modal_selector)
                                            modal_content = modal_element.text
                                            row_dict["ModalContent"] = modal_content
                                            tableDriver.driver.refresh()

                                        except Exception as e:
                                            print(e)
                                            continue
                                    else:
                                        tableDriver.driver.back()

                                    tableDriver.wait().until(
                                        EC.presence_of_all_elements_located(
                                            (By.CSS_SELECTOR, selector)
                                        ))
                                    clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, selector)
                                    row_element = clickable_rows[index]
                                    row_links = row_element.find_elements(By.TAG_NAME, "a")
                                except Exception as e:
                                    print(e)
                            row_dict["Urls"] = row_urls
                        else:
                            # If no direct link, click the row to determine the URL change
                            new_url = tableDriver.driver.current_url
                            try:
                                tableDriver.driver.execute_script("arguments[0].click();", row_element)
                                time.sleep(2)  # Wait for potential UI change
                                new_url = tableDriver.driver.current_url
                                if new_url != tableDriver.driver.current_url:
                                    row_dict["Url"] = new_url
                                    tableDriver.driver.back()
                                    tableDriver.wait().until(
                                        EC.presence_of_all_elements_located(
                                            (By.CSS_SELECTOR, f"{table_selector} tr.clickable"))
                                    )
                            except Exception as e:
                                print(f"Row click failed: {e}")
                                pass
                        all_rows_with_urls.append(row_dict)

                    except Exception as e:
                        print(f"Overall handling error: {e}")
                        all_rows_with_urls.append(row_dict)
                        continue

                # Check for the Next Page button
                next_button_selector = "nav a.pagination-link.pagination-next"
                try:
                    next_button = tableDriver.driver.find_element(By.CSS_SELECTOR, next_button_selector)
                    disabled_attr = next_button.get_attribute("disabled")
                    if str(disabled_attr) == "disabled" or str(disabled_attr) == "true":
                        continue
                    tableDriver.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    next_button.click()
                    time.sleep(1)
                    # tableDriver.action().move_to_element(next_button).click().perform()
                except:
                    break
                time.sleep(2)
                page_count += 1

        except Exception as e:
            print(f"Error: {e}")
        finally:
            tableDriver.quit()

        return all_rows_with_urls

    def extract_row_data2(self, table_selector: str = "table") -> [{}]:
        # if not self.safe_find_element(By.CSS_SELECTOR, f"{table_selector} tr.clickable"):
        #     return []
        tableDriver = self.new()
        tableDriver.add_cookies(self.get_cookies())
        all_rows_with_urls = []  # Final list to return
        max_pages = 20  # Safety limit to avoid infinite loops
        page_count = 0

        try:
            # 1) Load the page
            tableDriver.open(
                url=self.driver.current_url,
                username=self.login_details.username,
                password=self.login_details.password,
            )

            while True:
                if page_count >= max_pages:
                    break

                attempts = [
                    f"{table_selector} tr.clickable",
                    f"{table_selector} tr"
                ]
                selector = f"{table_selector} tr.clickable"
                for attempt in attempts:
                    try:
                        clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, attempt)
                        if clickable_rows:
                            selector = attempt
                            break
                    except Exception as e:
                        continue

                tableDriver.wait().until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )

                table_data = tableDriver.extract_all_tables()  # returns a list of row dicts
                clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, selector)
                row_count = min(len(clickable_rows), len(table_data))

                for index in range(row_count):

                    try:
                        clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, selector)
                        if index >= len(clickable_rows): break

                        row_dict = table_data[index]
                        row_element = clickable_rows[index]
                        """
                        TODO: 
                        
                        **SETUP**
                            1. Each row could be 'clickable' itself. 
                            2. Each row could have attributes that are <a> links to an entirely different url/page, it will just hide the url.
                            3. Each row could have attributes that are <a> links to a popup 'modal' of somekind. 
                        **GOAL**
                            1. Handle the row click, drive/get the url, add it to the row_dict, drive back, continue on. The point is to get the final url for later deeper extraction.
                            2. Handle each individual row attribute click, either go to the page, get the url, come back, continue.
                                OR
                                Open the modal, grab the content, close modal, add content to row_dict, continue.
                            3. Handle edge cases. Row headers, etc.
                        """



                        new_url = tableDriver.driver.current_url

                        try:
                            tableDriver.driver.execute_script("arguments[0].click();", row_element)
                            time.sleep(2)  # Wait for potential UI change
                            new_url = tableDriver.driver.current_url
                        except Exception as e:
                            print(e)
                            pass

                        if clickable_mode == "row":
                            row_dict["Url"] = new_url
                            tableDriver.driver.back()
                            tableDriver.wait().until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"{table_selector} tr.clickable"))
                            )
                        elif clickable_mode == "link":
                            pass
                        elif clickable_mode == "view":
                            # Handle modal popup
                            try:
                                modal_selector = "div.modal, div.full-screen-modal, div.responses-modal-body"  # Adjust selector for both modal types
                                tableDriver.wait().until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector))
                                )

                                modal_element = tableDriver.driver.find_element(By.CSS_SELECTOR, modal_selector)
                                modal_content = modal_element.text
                                row_dict["ModalContent"] = modal_content

                                close_button_selectors = ["div.modal button.close",
                                                          "div.full-screen-modal button.close",
                                                          "div.full-screen-modal button.button.is-text.close-button",
                                                          "div.full-screen-modal button button.is-text.close-button",
                                                          "button button.is-text.close-button",
                                                          "button button.is-ghost"
                                                          ]
                                close_button = None
                                for selector in close_button_selectors:
                                    try:
                                        close_button = tableDriver.driver.find_element(By.CSS_SELECTOR, selector)
                                        break
                                    except:
                                        continue
                                if close_button:
                                    close_button.click()
                            except Exception as modal_error:
                                print(f"Modal handling error: {modal_error}")
                                all_rows_with_urls.append(row_dict)
                                continue
                    except Exception as e:
                        print(f"Overall handling error: {e}")
                        all_rows_with_urls.append(row_dict)
                        continue
                    all_rows_with_urls.append(row_dict)

                # Check for Next page button
                next_button_selector = "nav a.pagination-link.pagination-next"
                try:
                    next_button = tableDriver.driver.find_element(By.CSS_SELECTOR, next_button_selector)
                    disabled_attr = next_button.get_attribute("disabled")
                    if str(disabled_attr) == "disabled" or str(disabled_attr) == "true":
                        break
                    tableDriver.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    tableDriver.action().move_to_element(next_button).click().perform()
                except:
                    break
                time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            tableDriver.quit()
        return all_rows_with_urls
    def extract_clickable_row_data(self, table_selector: str = "table") -> [{}]:

        if not self.safe_find_element(By.CSS_SELECTOR, f"{table_selector} tr.clickable"):
            return []
        tableDriver = self.new()
        all_rows_with_urls = []  # Final list to return
        max_pages = 20  # Safety limit to avoid infinite loops, if desired
        page_count = 0

        try:
            # 1) Load the page
            tableDriver.open(
                url=self.driver.current_url,
                username=self.login_details.username,
                password=self.login_details.password
            )

            while True:
                # Stop if we've paginated too many times (optional safeguard).
                if page_count >= max_pages:
                    break

                # 2) Wait for at least one clickable table row to appear
                tableDriver.wait().until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"{table_selector} tr.clickable"))
                )

                # --- A) Extract row data for the (assumed) single table on this page ---
                table_data = tableDriver.extract_all_tables()  # returns a list of row dicts

                # --- B) Find all clickable rows in the DOM ---
                clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr.clickable")

                # Make sure we don’t exceed the bounds if there are non-clickable rows
                row_count = min(len(clickable_rows), len(table_data))

                # --- C) For each clickable row, click to get the URL ---
                for index in range(row_count):
                    # Re-locate rows on each iteration (DOM can change after clicks/back)
                    clickable_rows = tableDriver.driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr.clickable")
                    if index >= len(clickable_rows): break

                    # Grab the row dict from table_data (naive assumption: same order as in the DOM)
                    row_dict = table_data[index]

                    # Click the row
                    row_element = clickable_rows[index]
                    row_element.click()
                    time.sleep(2)  # Or a more precise wait for navigation

                    # Capture the new URL
                    new_url = tableDriver.driver.current_url
                    # Attach it to the row dict
                    row_dict["Url"] = new_url

                    # Store this row (with URL) in our master list
                    all_rows_with_urls.append(row_dict)

                    # Navigate back to the table page
                    tableDriver.driver.back()
                    tableDriver.wait().until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, f"{table_selector} tr.clickable")
                        )
                    )

                # --- C) Check for Next page button ---
                next_button_selector = "nav a.pagination-link.pagination-next"
                try:
                    next_button = tableDriver.driver.find_element(By.CSS_SELECTOR, next_button_selector)
                    disabled_attr = next_button.get_attribute("disabled")
                    if str(disabled_attr) == "disabled" or str(disabled_attr) == "true":
                        break
                    tableDriver.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    tableDriver.action().move_to_element(next_button).click().perform()
                except: break
                time.sleep(2)
        except Exception as e:  print(f"Error: {e}")
        finally: tableDriver.quit()
        return all_rows_with_urls
if __name__ == '__main__':
    email = "jperson@parkcitysoccer.org"
    password = "Philly23!"
    RaiWebPageScrape().scrape_light(url="https://playmetrics.com/director/programs/49521", username=email, password=password)