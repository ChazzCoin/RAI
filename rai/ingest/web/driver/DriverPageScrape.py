import asyncio
from typing import Optional

from F import LIST
from F.LOG import Log
from selenium.webdriver.common.by import By

from rai.ingest.DataImport import RaiDataImporter
from rai.ingest.web.WebModels import FullDocumentPageAnalysisModel
from rai.ingest.providers.WebSourceProvider import IngestWebSourceProvider
from rai.ingest.web.driver.DriverSiteMapper import RaiWebSiteMapper
from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor
from rai.ingest.web.soup.UrlExtractor import WebUrlExtractor
from rai.ingest.web.soup.WebExtractor import WebActionExtractor
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)


Log = Log("RaiWebPageScrape")
""" Master Web Driver """
class RaiWebPageScrape(RaiWebSiteMapper):
    pages = []

    async def pageThreader(self, prefix:str, url:str):
        crawler = IngestWebSourceProvider()
        await crawler.url_recon(url)
        self.current_url = url
        self.add_update_crawler_queue(crawler.all_links)
        count = 0
        while self.to_visit_urls:
            if count == 3: break
            next = self.to_visit_urls.pop()
            self.page_recon(next)
            self.visited_urls.add(next)
            count = count + 1
        RaiDataImporter.import_web_docs(prefix, url, self.cache)
    def import_single_page(self, prefix:str, url: str, username=None, password=None):
        self.page_recon(url, username, password)
        RaiDataImporter.import_web_docs(prefix, url, self.cache)

    def test(self, url: str, username=None, password=None):
        self.open(url, username, password)
        data = []
        tab = 1
        dont_stop = True
        while dont_stop:
            column_data = self.extract_columns()
            table_data = self.extract_all_tables()
            table_data2 = self.extract_table_data()
            events = self.extract_calendar_events()
            player = self.extract_player_profile()
            temp = {
                "columns": column_data,
                "tables": table_data,
                "table_data": table_data2,
                "events": events,
                "player": player
            }
            data.append(temp)
            if self.click_nav_tab(tab):
                self.post_open()
                tab = tab + 1
            else:
                dont_stop = False
        print("done")

    def safe_get_children_text(self, element):
        # Set up the WebDriver
        if not element: return None
        data = []
        try:
            # Use XPath to find all child elements recursively
            children = element.find_elements(By.XPATH, './/*')

            for child in children:
                text = self.get_safe_text(child)
                if text is not None: data.append(text)
            return data
        except Exception as e:
            print(f"An error occurred: {e}")
            return data

    def get_safe_text(self, element):
        try:
            if self.has_text(element):
                return element.text
            return None
        except:
            return None
    def has_text(self, element) -> bool:
        try:
            if not element: return False
            if not element.text: return False
            if type(element.text) not in [str]: return False
            if element.text == "": return False
            if element.text == " ": return False
            return True
        except:
            return False

    def extract_columns(self):
        data = {}
        try:
            columns = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'column')]"
            )
            p = 0
            for c in columns:
                contents = c.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'content')]"
                )
                i = 0
                for column in contents:
                    if not self.has_text(column): continue
                    data[f"{str(p)}-{str(i)}"] = str(column.text)
                    i = i + 1
                p = p + 1
            return list(set(data.values()))
        except:
            return data
    def extract_team_profile(self):
        data = {}
        try:
            team_elem = self.driver.find_element(
                By.XPATH,
                "//*[contains(@class, 'team')]"
            )
            team_name = team_elem.find_element(
                By.XPATH,
                "//*[contains(@class, 'title')]"
            )
            data["name"] = str(team_name.text)
            return data
        except:
            return data
    def extract_player_profile(self):
        data = {}
        try:
            player_profile = self.driver.find_element(
                By.XPATH,
                "//*[contains(@class, 'player') and contains(@class, 'profile')]"
            )
            player_name = player_profile.find_element(
                By.XPATH,
                "//*[contains(@class, 'player') and contains(@class, 'name')]"
            )
            player_fields = player_profile.find_elements(
                By.XPATH,
                "//*[contains(@class, 'field')]"
            )
            data = { "name": player_name.text }
            for field in player_fields:
                try:
                    field_key = field.find_element(
                        By.TAG_NAME, "label"
                    )
                    field_value = field.find_element(
                        By.TAG_NAME,
                        "div"
                    )
                    data[str(field_key.text)] = str(field_value.text)
                except:
                    continue
            return data
        except:
            return data
    def page_recon(self, url: str, username=None, password=None) -> []:
        self.open(url, username, password)
        tab = 1
        dont_stop = True
        while dont_stop:
            page = self.page_extract(url)
            if page: self.pages.append(page)
            if self.click_nav_tab(tab):
                self.post_open()
                tab = tab + 1
            else:
                dont_stop = False
        return self.pages

    def page_extract(self, url: str) -> Optional[FullDocumentPageAnalysisModel]:
        try:
            header_content = f"PAGE HEADER:\n{url}\n{self.page_title}\n"
            body_content = "PAGE BODY:\n"
            footer_content = "PAGE FOOTER:\n"
            Log.i("Extracting Page.")

            player = self.extract_player_profile()
            if player: header_content += f"{str(player)}\n"

            column_data = self.extract_columns()
            if column_data:
                if type(column_data) == list:
                    for col in column_data:
                        footer_content += f"{str(col)}\n"
                else:
                    footer_content += f"{str(column_data)}\n"

            """ Extract Body """
            body = WebBodyExtractor.pipeline(self.driver.page_source)
            body_content += f"{body.combined_text}\n"

            """ Extract All Table Data """
            table_data1 = self.extract_all_tables()
            table_data2 = self.extract_table_data()
            table_data = LIST.flatten(LIST.merge_lists(table_data1, table_data2))
            if table_data:
                for item in table_data:
                    body_content +=  f"{str(item)}\n"

            """ Extract Events """
            events = self.extract_calendar_events()
            if events:
                if type(events) == list:
                    for evn in events:
                        body_content += f"{str(evn)}\n"
                else:
                    body_content += f"{str(events)}\n"

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

            final_content = f"{header_content}\n{body_content}\n{footer_content}"
            print(final_content)
            """ Add New Urls to Queue """
            self.add_update_crawler_queue(LIST.merge_lists(urls, urls2))

            """ Page Extraction Model """
            page = DocumentAnalysisAgent.analyze_text_async(
                content=final_content,
                url=self.driver.current_url,
                page_title=self.page_title,
                parent_id=self.site_id,
                page_id=self.page_id,
                page_number=f"{len(self.pages) + 1}",
            )
            page.title = self.page_title
            page.source = url
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
    urls = [
        "https://www.parkcityextremecup.com/heber-venues-original-copy",
        "https://www.parkcityextremecup.com/oakley-directions-maps",
        "https://www.parkcityextremecup.com/referee-faqs",
        "https://www.parkcityextremecup.com/lodgingv2",
        "https://www.parkcityextremecup.com/where-to-eat",
        "https://www.parkcityextremecup.com/where-to-shop",
        "https://www.parkcityextremecup.com/things-to-do",
        "https://www.parkcityextremecup.com/business-services",
        "https://www.parkcityextremecup.com/who-to-call-1",
        "https://www.parkcityextremecup.com/custom-apparel-1"
    ]
    asyncio.run(RaiWebPageScrape().pageThreader("busa2025.1", "https://birminghamunited.com"))
    # print(ps)
    # for url in urls:
    #     RaiWebPageScrape().import_single_page(prefix="pcsc2025.4", url=url, username=email, password=password)