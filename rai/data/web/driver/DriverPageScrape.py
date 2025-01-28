from typing import Optional

from F import DICT, LIST
from F.LOG import Log
from selenium.webdriver.common.by import By

from rai.composers.TextAnalysisAgent import TextAnalysisAgent

from rai.data.web.WebModels import PageExtractDetails
from rai.data.web.driver.WebDriver import RaiWebDriver

from rai.data.web.soup.BodyExtractor import WebBodyExtractor
from rai.data.web.soup.UrlExtractor import WebUrlExtractor
from rai.data.web.soup.WebExtractor import WebActionExtractor
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)


Log = Log("RaiWebPageScrape")
""" Master Web Driver """
class RaiWebPageScrape(RaiWebDriver):
    pages = []

    def scrape_page(self, url: str, username=None, password=None) -> Optional[PageExtractDetails]:
        try:
            self.open(url, username, password)
            Log.i("Extracting Page.")

            """ Extract All Table Data """
            table_data = self.extract_all_tables()

            """ Extract Events """
            events = self.extract_calendar_events()

            """ Extract PDF Files """
            pdfs = self.extract_pdf_urls()
            pdf_texts = self.extract_text_from_pdf_urls(pdfs)

            """ Extract Images """
            images = self.extract_image_urls()
            image_texts = self.extract_text_from_image_urls(images)

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
            self.add_update_crawler_queue(LIST.merge_lists(urls, urls2))

            """ Page Extraction Model """
            page = TextAnalysisAgent.analyze_text_async(
                content=body.combined_text,
                url=self.current_url,
                page_title=self.page_title
            )
            page.title = self.page_title
            page.url = url
            page.author = "RaiWebPageScrape"
            page.events = LIST.merge_lists(page.events, events)
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

if __name__ == '__main__':
    email = "jperson@parkcitysoccer.org"
    password = "Philly23!"
    RaiWebPageScrape().scrape_page(url="https://playmetrics.com/teams/194128/summary", username=email, password=password)