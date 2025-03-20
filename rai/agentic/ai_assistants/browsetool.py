import asyncio
import json
import re
from collections import deque
from typing import Optional, Type, Any, List, Dict, Coroutine, Tuple, Union

from F import LIST, DICT
from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import BrowserState
from browser_use.dom.service import DomService
from bs4 import BeautifulSoup
from playwright.async_api import Page, Dialog
from pydantic import Field, BaseModel, HttpUrl
from watchfiles import awatch

from rai.agentic.aether.schema import AgentState
from rai.agentic.aether.tool import ToolResult
from rai.agentic.aether.UseBrowserConfig import config
from rai.agentic.ai_plugins.reason import rAssistantReasoningPlugin, SearchTerms, DOMIndex, Objective
from rai.agentic.ai_plugins.tool import ToolEngine
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor
from rai.internal.clients.ioredis_client import IORedis

MAX_LENGTH = 2000

_BROWSER_DESCRIPTION = """
Interact with a web browser to perform various actions such as navigation, element interaction,
content extraction, and tab management. Supported actions include:
- 'navigate': Go to a specific URL
- 'click': Click an element by index
- 'input_text': Input text into an element
- 'screenshot': Capture a screenshot
- 'get_html': Get page HTML content
- 'get_text': Get text content of the page
- 'read_links': Get all links on the page
- 'execute_js': Execute JavaScript code
- 'scroll': Scroll the page
- 'switch_tab': Switch to a specific tab
- 'new_tab': Open a new tab
- 'close_tab': Close the current tab
- 'refresh': Refresh the current page
"""


class TabInfo(BaseModel):
    # Assuming TabInfo structure; update this according to actual implementation
    id: int
    title: str
    url: HttpUrl


class BrowserToolState(BaseModel):
    url: HttpUrl
    title: str
    tabs: List['TabInfo']
    screenshot: Optional[str] = None
    pixels_above: int = 0
    pixels_below: int = 0
    browser_errors: List[str] = Field(default_factory=list)


class BrowserTool2(ToolEngine):

    @staticmethod
    def _required_model() -> Type[BaseModel]:
        pass

    @staticmethod
    def module_name() -> str:
        return 'browse'

    @staticmethod
    def _required_data_model_type() -> Type[ToolResult]:
        return ToolResult

    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You are a reasoning assistant who can control a web browser.
            You take in a request, develop a web search plan and accomplish the task.
        """

    @staticmethod
    def ToolState() -> Type[BrowserToolState]:
        return BrowserToolState

    @staticmethod
    def tool_assistant_name() -> str:
        return "Web Browser Assistant"

    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION

    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)

    page: Optional[Page] = None
    previous_page: Optional[Page] = None
    current_page: Optional[Page] = None

    pub = IORedis

    def __init__(self):
        super().__init__()

    async def start_screenshot_stream(self, channel_name="agent", interval=10):
        async def publish_screenshots():
            while True:
                try:
                    self.log_voice("WEBSOCKET: Sending screenshot")
                    try:
                        page = await self.context.get_current_page()
                        screenshot_bytes = await page.screenshot(type='jpeg', quality=70)
                        await self.pub.redis_client.publish(channel_name, screenshot_bytes)
                        self.log_voice("WEBSOCKET: Screenshot Sent")
                    except Exception as e:
                        self.log_voice(f"WEBSOCKET: Screenshot Failed: {e}")
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    self.log_voice(f"WEBSOCKET: Screenshot stream cancelled.")
                    break
                except Exception as e:
                    self.log_voice(f"WEBSOCKET: Screenshot stream error: {e}")
                    await asyncio.sleep(interval)
        self.log_voice("WEBSOCKET: Starting screenshot stream")
        asyncio.create_task(publish_screenshots())
    @property
    def safe_context(self) -> Optional[BrowserContext]:
        if type(self.context) in [BrowserContext]: return self.context
        return None
    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool(function_name="google_search"),
            self.get_tool(function_name="navigate"),
            self.get_tool(function_name="click"),
            self.get_tool(function_name="input_text"),
            self.get_tool(function_name="execute_js"),
            self.get_tool(function_name="scroll"),
            self.get_tool(function_name="switch_tab"),
            self.get_tool(function_name="new_tab"),
            self.get_tool(function_name="close_tab"),
            self.get_tool(function_name="refresh_page")
        ]
    async def __ensure_browser_initialized(self) -> Optional[BrowserContext]:
        """Ensure browser and context are initialized."""

        if type(self.context) in [BrowserContext]: return self.context
        await self.pub.connect()
        await self.start_screenshot_stream()

        browser_config_kwargs = {
            "headless": config.browser_config.headless or False,
            "disable_security": config.browser_config.disable_security or False
        }

        if config.browser_config:
            from browser_use.browser.browser import ProxySettings

            # Handle proxy settings.
            if config.browser_config.proxy and config.browser_config.proxy.server:
                browser_config_kwargs["proxy"] = ProxySettings(
                    server=config.browser_config.proxy.server,
                    username=config.browser_config.proxy.username,
                    password=config.browser_config.proxy.password,
                )

            browser_attrs = [
                "headless",
                "disable_security",
                "extra_chromium_args",
                "chrome_instance_path",
                "wss_url",
                "cdp_url",
            ]

            for attr in browser_attrs:
                value = getattr(config.browser_config, attr, None)
                if value is not None:
                    if not isinstance(value, list) or value:
                        browser_config_kwargs[attr] = value

        self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))
        context_config = BrowserContextConfig()
        # If there is context config in the config, use it.
        if (
            config.browser_config
            and hasattr(config.browser_config, "new_context_config")
            and config.browser_config.new_context_config
        ):
            context_config = config.browser_config.new_context_config
        context = await self.browser.new_context(context_config)
        self.dom_service = DomService(await context.get_current_page())
        self.context = context
        return context

    """ OUTPUT """
    def output_search_results(self, html: str) -> List[ToolResult]:
        self.soup(html)
        results = []

        for g in self.soup.select('div.tF2Cxc'):
            title_el = g.select_one('h3')
            link_el = g.select_one('a')
            desc_el = g.select_one('div.VwiC3b')

            if not title_el or not link_el:
                continue

            title = title_el.get_text() if title_el else ''
            url = link_el['href']
            description_el = g.select_one('div.VwiC3b span.aCOpRe') or g.select_one('div.VwiC3b')
            description = description_el.get_text(strip=True) if (
                description_el := description_el) else ''

            results.append(ToolResult(
                result_type="search",
                url=url,
                description=description,
                title=title,
            ))
        return results
    async def output_with_summary(self, url, html) -> ToolResult:
        body = await WebBodyExtractor.pipeline_async(html)
        content = TextProcessor.TEXT_CLEANER(body.combined_text)
        if not TextProcessor.string_length_is_within(content, 100):
            content = await self.think_then_summarize(content)
        return ToolResult(
            output=f"BrowserTool: Navigated to [ {url} ]",
            result_type="search",
            action="search google",
            url=url,
            result=content
        )

    """
    CORE FUNCTIONS
    1. add_and_pass all core functions
    """
    async def deep_search(self, *search_terms:str) -> List[ToolResult]:
        if not self.is_setup: await self.setup_assistant("\n".join(search_terms))

        recon_step_count = 0
        if not search_terms: await self._get_set_search_terms()
        else: self.find_all_search_results()
        search_queue = deque(self.find_all_search_results() or [])
        while search_queue:
            term = search_queue.popleft()
            recon_step_count += 1
            self.log_voice(f"Deep Search step {recon_step_count}")
            self.log_voice(f"Deep Search term: {term}")
            result = await self.google_search(search_term=term.search_term)
            if result and type(result) in [list, tuple]:
                for item in result:
                    item.search_term = term
                self.add_results(result)
            else:
                result.search_term = term
                result.result_type = "search"
                result.result_status = "ready"
                self.add_result(result)
            self.log_voice(f"Deep Search Step {recon_step_count}")
        return await self._navigate_search_results()
    async def google_search(self, search_term: str) -> ToolResult:
        self.log_voice("google_search called.")
        url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
        if not url:
            self.log_voice("Failed: URL was not generated.")
            return ToolResult(error="URL is required for 'navigate' action")
        self.log_voice(f"Generated URL successfully. URL: [ {url} ]")
        self.log_voice("Initiating navigation.")
        try:
            result = await self.navigate(url, "search")
            self.log_voice("Navigation completed successfully.")
            return result
        except Exception as e:
            self.log_voice(f"Navigation failed: [ {str(e)} ]")
            self.log_thought(f"Error navigating [ {str(e)} ]")
            return ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url,
                              error=f"Error navigating [ {str(e)} ]")
    async def navigate(self, url: Optional[str], output:Optional[str]='html') -> None | ToolResult | list[ToolResult]:
        self.log_voice("Navigate called.")
        context = await self.__ensure_browser_initialized()
        self.log_voice(f"Navigate: Browser initialized: {'Yes' if context else 'No'}")
        if not url:
            self.log_voice("Navigate: Failed: URL is required but missing.")
            return ToolResult(error="URL is required for 'navigate' action")
        self.log_voice(f"Navigate: URL validated successfully. URL: [ {url} ]")

        async def handle_dialog(dialog: Dialog) -> None:
            print(f"Dialog detected: {dialog.message}")
            await dialog.dismiss()
            print("Dialog dismissed")
        async def handle_load(page: Page) -> None:
            print(f"WebSocket: Page Loaded: {page.url}")
            html = self.safe_context.get_page_html()
            content = self.html_to_content(html)
            await self.think_then_summary_report(content, ensure_length=10000)

        try:
            if type(self.page) not in [Page]:
                self.page = await context.get_current_page()
            self.previous_page = self.page
            self.page.once("dialog", handle_dialog)
            self.page.once("load", handle_load)
            self.log_voice(f"Navigate: Going to page: [ {url} ]")
            await self.page.goto(url, timeout=5000, wait_until="domcontentloaded")

            self.log_voice("Navigate: Page loaded successfully.")
            html = await context.get_page_html()
            self.log_voice("Navigate: HTML content retrieved successfully.")

            toolResult = None

            if output == 'pass':
                self.log_voice("Navigate: Handling pass.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, result="passthrough")

            if output == 'summary':
                self.log_voice("Navigate: Handling summarized content.")
                toolResult = await self.output_with_summary(url, html)

            elif output == 'search':
                self.log_voice("Navigate: Handling parsed search results.")
                toolResult = self.output_search_results(html=html)

            elif output == 'html':
                self.log_voice("Navigate: Handling raw HTML content.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, result=html)

            return toolResult
        except Exception as e:
            self.log_voice(f"Navigate: Navigation failed: [ {str(e)} ]")
            self.log_thought(f"Error navigating [ {str(e)} ]")
            return ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, error=f"Error navigating [ {str(e)} ]")
    async def click(self, index: Optional[int]) -> ToolResult:
        self.log_voice(f"click called with index: [ {index} ]")
        if index is None:
            self.log_voice("Click failed: No index provided.")
            return ToolResult(error="Index is required for 'click' action")
        element = await self.context.get_dom_element_by_index(index)
        self.log_voice(f"Element retrieval: {'Success' if element else 'Failed'}")
        if not element:
            return ToolResult(error=f"Element with index {index} not found")
        download_path = await self.context._click_element_node(element)
        self.log_voice(f"Element clicked: {'Success' if download_path else 'No download initiated'}")
        output = f"Clicked element at index {index}"
        if download_path:
            output += f" - Downloaded file to {download_path}"
        return ToolResult(output=output)
    async def input_text(self, index: Optional[int], text: Optional[str]) -> ToolResult:
        self.log_voice("input_text called.")
        if index is None or not text:
            self.log_voice("Input text failed: Index or text missing.")
            return ToolResult(error="Index and text are required for 'input_text' action")
        element = await self.context.get_dom_element_by_index(index)
        self.log_voice(f"Element retrieval for input: {'Success' if element else 'Failed'}")
        if not element:
            return ToolResult(error=f"Element with index {index} not found")
        await self.context._input_text_element_node(element, text)
        self.log_voice("Text input successful.")
        return ToolResult(output=f"Input '{text}' into element at index {index}")
    async def screenshot(self) -> ToolResult:
        self.log_voice("screenshot called.")
        screenshot = await self.context.take_screenshot(full_page=True)
        self.log_voice(f"Screenshot captured successfully.")
        return ToolResult(output=f"Screenshot captured (base64 length: {len(screenshot)})", system=screenshot)
    async def refresh_page(self) -> ToolResult:
        self.log_voice("refresh_page called.")
        await self.context.refresh_page()
        self.log_voice("Page refreshed successfully.")
        return ToolResult(output="Refreshed current page")
    async def get_html(self) -> ToolResult:
        html = await self.context.get_page_html()
        truncated = html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
        return ToolResult(output=truncated)
    async def get_text(self) -> ToolResult:
        text = await self.context.execute_javascript("document.body.innerText")
        print("BrowserUseTool: get_text: ", text)
        return ToolResult(output=text)
    async def read_links(self) -> ToolResult:
        links = await self.context.execute_javascript(
            "document.querySelectorAll('a[href]').forEach((elem) => {if (elem.innerText) {console.log(elem.innerText, elem.href)}})"
        )
        return ToolResult(output=links)
    async def execute_js(self, script: Optional[str]) -> ToolResult:
        if not script:
            return ToolResult(error="Script is required for 'execute_js' action")
        result = await self.context.execute_javascript(script)
        return ToolResult(output=str(result))
    async def scroll(self, scroll_amount: Optional[int]) -> ToolResult:
        if scroll_amount is None:
            return ToolResult(error="Scroll amount is required for 'scroll' action")
        await self.context.execute_javascript(f"window.scrollBy(0, {scroll_amount});")
        direction = "down" if scroll_amount > 0 else "up"
        return ToolResult(output=f"Scrolled {direction} by {abs(scroll_amount)} pixels")
    async def switch_tab(self, tab_id: Optional[int]) -> ToolResult:
        if tab_id is None:
            return ToolResult(error="Tab ID is required for 'switch_tab' action")
        await self.context.switch_to_tab(tab_id)
        return ToolResult(output=f"Switched to tab {tab_id}")
    async def new_tab(self, url: Optional[str]) -> ToolResult:
        if not url:
            return ToolResult(error="URL is required for 'new_tab' action")
        await self.context.create_new_tab(url)
        return ToolResult(output=f"Opened new tab with URL {url}")
    async def close_tab(self) -> ToolResult:
        await self.context.close_current_tab()
        return ToolResult(output="Closed current tab")
    async def go_home(self) -> ToolResult:
        return await self.navigate(url="https://www.raico.dev", output="page")
    async def get_current_state(self) -> ToolResult:
        """Get the current browser state as a ToolResult."""
        async with self.lock:
            try:
                context = await self.__ensure_browser_initialized()
                state = await context.get_state()
                state_info = {
                    "url": state.url,
                    "title": state.title,
                    "tabs": [tab.model_dump() for tab in state.tabs],
                    "interactive_elements": state.element_tree.clickable_elements_to_string(),
                }
                tr = ToolResult(
                    output=str(json.dumps(state_info)),
                    result_type="tool_state"
                )
                return self.add_and_pass(tool=tr)
            except Exception as e:
                return self.add_and_pass(tool=ToolResult(error=f"Failed to get browser state: {str(e)}"))

    """ DEEP SEARCH MODE """
    async def _navigate_search_results(self, tool_results: List[ToolResult]=None) -> List[ToolResult]:
        recon_step_count = 0
        search_queue = deque(tool_results or self.find_all_search_results() or [])
        while search_queue:
            search = search_queue.popleft()
            recon_step_count += 1
            self.log_voice(f"Executing Search Result step {recon_step_count}")
            self.log_voice(f"Search term: {search.search_term}, Search Url: {search.url}")
            result = await self.navigate(url=search.url, output='summary')
            result.attach_search_parent(search)
            self.log_voice(f"Extracting Search Result Step {recon_step_count}")
        self.log_voice("Finished handling Search results.")
        await self.go_home()
        return tool_results
    async def _get_set_search_terms(self) -> Optional[SearchTerms]:
        result = await self.llm().formatter_async(
            text=f"""
                {self.tool_plan.inject_objective_prompt()}
                **Based on the objective, create a list of at least 10 web search terms to search google with.**
            """,
            model=SearchTerms,
            system=f"""
               **You are a master of creating concise and yet detailed search terms for finding specific objectives and goals**
                    Example: "who hosted the 2025 oscars?"
                    Example: "what is some of the latest geo-political news?"
                    Example: "What are the scores of the latest international soccer games?"
                    Example: "When is the next olympics?"
                {self.inject_tool_options_prompt()}
                {self.tool_plan.inject_objective_prompt()}
                {self.tool_plan.inject_user_request()}
            """,
        )

        if result:
            self.log_voice(f"Search terms for {self.tool_plan.overall_objective}\n {str(result.search_terms)}")
            self.tool_results.extend(result.search_terms)
        return result or None

if __name__ == "__main__":

    looper = asyncio.get_event_loop()
    # looper.run_until_complete(BrowserTool().run(request="Who were the last international soccer teams to play, who played and what were the scores?"))
    looper.run_until_complete(BrowserTool2().self_navigation("Go to facebook and go to mallory romeo's profile."))
