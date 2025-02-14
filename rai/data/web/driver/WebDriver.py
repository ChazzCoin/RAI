import time
import uuid

from F.LOG import Log
from rai.data.loaders.rai_loaders.BaseLoad import RaiDocCreator
from rai.data.web.driver.DriverExtractor import WebBaseExtract
from rai.data.web.RaiUrl import RaiUrl
from collections import deque
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

Log = Log("RaiWebPageScrape")
""" Master Web Driver """
class RaiWebDriver(WebBaseExtract, RaiDocCreator):
    site_id = None
    page_id = None
    site = None
    site_title = ""
    page_count = 0
    found_tables = []
    visited = set()
    recon_queue = deque()
    start_domain = None

    def __init__(self, open_url: str = None, username=None, password=None):
        super().__init__()
        self.site_id = str(uuid.uuid4())
        if open_url: self.open(open_url, username, password)

    @classmethod
    def new(cls): return cls()

    def open(self, url, username=None, password=None) -> { str:str }:
        Log.i("Opening URL:", url)
        self.base_url = RaiUrl(url)
        self.login(username, password)
        self.driver.get(url)
        self.visited_urls.add(url)
        self.post_open()
    def post_open(self):
        self.wait().until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.parse(self.driver.page_source)
        self.set_tab_count()
        self.do_infinite_scroll_down()
        time.sleep(1)
        self.do_infinite_scroll_up()
        time.sleep(1)
        self.page_id = str(uuid.uuid4())
