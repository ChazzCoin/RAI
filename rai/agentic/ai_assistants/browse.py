import asyncio
import json
import re
from collections import deque
from contextlib import asynccontextmanager
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
from rai.agentic.aether.UseBrowserConfig import config
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.ai_plugins.reason import rAssistantReasoningPlugin, SearchTerms, DOMIndex, Objective
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


class BrowserTool(rAssistantReasoningPlugin):

    @staticmethod
    def response_model() -> Type[BaseModel]:
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

    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "input_text",
                    "screenshot",
                    "get_html",
                    "get_text",
                    "execute_js",
                    "scroll",
                    "switch_tab",
                    "new_tab",
                    "close_tab",
                    "refresh",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate' or 'new_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click' or 'input_text' actions",
            },
            "text": {"type": "string", "description": "Text for 'input_text' action"},
            "script": {
                "type": "string",
                "description": "JavaScript code for 'execute_js' action",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll' action",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "navigate": ["url"],
            "click": ["index"],
            "input_text": ["index", "text"],
            "execute_js": ["script"],
            "switch_tab": ["tab_id"],
            "new_tab": ["url"],
            "scroll": ["scroll_amount"],
        },
    }

    lock: asyncio.Lock = asyncio.Lock()
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)

    page: Optional[Page] = None
    previous_page: Optional[Page] = None
    current_page: Optional[Page] = None
    decision_log = []
    summary_report = ""
    tool_state: Optional[ToolState] = Field(default=None, exclude=True)
    search_terms: List[str] = []
    pending_search_results: List[ToolResult] = []

    """ SETUP """
    def _setup_assistant(self, user_request: str, **attached_data):
        # The Assistant Process Log
        self.assistant_log("Setting up reasoning assistant.")
        self.assistant_log("Gathering and formatting initial request, rules, documentation and data.")

        # Assistant Rules Data
        self.ext_documentation_tagged = self.map_external_class()
        self.assistant_rules_tagged = self.tag_data("RULES", self.assistant_rules())
        self.assistant_system_prompt = self.tag_data(
            "ASSISTANT_RULES_AND_INFO",
            self.chain_data(self.ext_documentation_tagged, self.assistant_rules())
        )

        # User Request Data
        self.attached_data_tagged = self.tag_data("ATTACHED_DATA", str(attached_data))
        self.initial_request_tagged = self.tag_data("INITIAL_REQUEST", user_request)
        self.user_request_prompt = self.tag_data(
            "USER_REQUEST_PROMPT",
            f"{self.attached_data_tagged}\n{self.initial_request_tagged}"
        )


    username = "chazzromeo@gmail.com"
    password = "laurelpark8294"

    pub = IORedis

    def __init__(self):
        super().__init__()

    async def start_screenshot_stream(self, channel_name="agent", interval=10):
        async def publish_screenshots():
            while True:
                try:
                    self.assistant_log("WEBSOCKET: Sending screenshot")
                    try:
                        page = await self.context.get_current_page()
                        screenshot_bytes = await page.screenshot(type='jpeg', quality=70)
                        await self.pub.redis_client.publish(channel_name, screenshot_bytes)
                        self.assistant_log("WEBSOCKET: Screenshot Sent")
                    except Exception as e:
                        self.assistant_log(f"WEBSOCKET: Screenshot Failed: {e}")
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    self.assistant_log(f"WEBSOCKET: Screenshot stream cancelled.")
                    break
                except Exception as e:
                    self.assistant_log(f"WEBSOCKET: Screenshot stream error: {e}")
                    await asyncio.sleep(interval)
        self.assistant_log("WEBSOCKET: Starting screenshot stream")
        asyncio.create_task(publish_screenshots())

    @property
    def safe_context(self) -> Optional[BrowserContext]:
        if type(self.context) in [BrowserContext]: return self.context
        return None

    def get_browser_tools(self):
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
    """ PARSING """
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

    def __ensure_length(self, content, length:int=10000):
        return TextProcessor.ensure_within_limit(content, length)
    async def __parse_html_to_content(self, html):
        body = await WebBodyExtractor.pipeline_async(html)
        return TextProcessor.TEXT_CLEANER(body.combined_text)
    async def __summarize(self, content, ensure_length:int = 10000):
        content = self.__ensure_length(content, ensure_length)
        return self.llm().generate(user=content, system=f"""
            Read and Analyze this HTML based extracted content from a website page.
            **REMOVE all web/html specific information**
            **CONTEXT FOR SUMMARIZATION = {self.overall_objective}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.initial_request_tagged}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """)
    async def __generate_report(self, content, ensure_length:int = 10000) -> str:
        self.assistant_log("Updating Report Summary with new page...")
        if self.summary_report == "":
            report = await self.__summarize(content, ensure_length)
            if report:
                self.summary_report = report
                return report

        content = self.__ensure_length(content, ensure_length)
        prompt = f"""
            <CURRENT_SUMMARY>
                {self.summary_report}
            </CURRENT_SUMMARY>
            <NEW_CONTENT_TO_ADD_TO_SUMMARY>
                {content}
            </NEW_CONTENT_TO_ADD_TO_SUMMARY>
        """
        report = await self.llm().generate_async(user=prompt, system=f"""
            **You keep and update an on-going summary of web pages that have been visted.**
            You are to creating an on-going summary or timeline of web browsing results.
            You will 'merge' the results together into 1 single memory timeline.
            **CONTEXT FOR SUMMARIZATION = {self.overall_objective}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.initial_request_tagged}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """)
        if report and str(report) != "":
            self.assistant_log(f"Updated Report Summary:\n{report}")
            self.summary_report = report
        return report

    """ OUTPUT """
    def output_search_results(self, html: str) -> List[ToolResult]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        for g in soup.select('div.tF2Cxc'):
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
            content = await self.__summarize(content)
        return ToolResult(
            output=f"BrowserTool: Navigated to [ {url} ]",
            result_type="search",
            action="search google",
            url=url,
            result=content
        )

    """ ASSISTANT """
    async def self_navigation(self, request: Optional[str] = None) -> str:
        self.state = AgentState.RUNNING
        # if request: self.update_memory("user", request)
        self._setup_assistant(user_request=request)
        await self._get_set_objective_async()
        await self._get_set_plan_async()

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (self.current_step_count < self.max_steps and self.state != AgentState.FINISHED):
                step: NextStepModel = await self._get_set_next_step_async()
                self.current_step_count += 1
                self.assistant_log(f"Executing step {self.current_step_count}/{self.max_steps}")
                object_r: ToolResult = await self._decide_and_act(step.next_step_or_action)
                self.import_result_and_pass(object_r)
                self.steps_taken.append(step)
                results.append(f"Step {self.current_step_count}")

            if self.current_step_count >= self.max_steps:
                self.current_step_count = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        resp = self.respond()
        return resp
    async def _decide_and_act(self, step) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tool_state = await self.get_current_state()

            decisions = ""
            for d in self.decision_log:
                data = DICT.get("function", d, None)
                func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
                args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
                temp = f"""
                    ----
                    Function Name: {func_name}
                    Function Arguments: {args_source}
                    ----
                """
                decisions += temp
            nav_prompt = f"""
                Review the following web html DOM index interactive elements.
                Based on the User Prompt, pick the index and tool function accordingly.
                <ASSISTANT_PROCESS_LOG>
                    {self.get_assistant_log_str() or 'Nothing has happen'}
                </ASSISTANT_PROCESS_LOG>
                <PROCESS_SUMMARY>
                    {self.summary_report or 'Nothing has happen'}
                </PROCESS_SUMMARY>
                <PAST_FUNCTION_CALLS>
                    {decisions}
                </PAST_FUNCTION_CALLS>
                <CURRENT_BROWSER_STATE>
                    {tool_state.output}
                </CURRENT_BROWSER_STATE>
            """
            step_prompt = f"""
                <USER_DATA>
                    Username/Email: {self.username}
                    Password: {self.password}
                </USER_DATA>
                <NEXT_STEP_TO_ACHIEVE>
                    {step}
                </NEXT_STEP_TO_ACHIEVE>
            """
            self.assistant_log("Attempting to Self Navigate...")
            decision = await self.llm().generate_function_async(
                user=step_prompt,
                system=nav_prompt,
                functions=self.get_browser_tools(),
                raw_result=True
            )
            self.assistant_log(f"Navigation decision made: [ {decision} ]")
            if decision:
                self.decision_log.extend(decision)
                action_result = await self.parse_and_call_function_async(decision)
                if action_result:
                    self.assistant_log(f"Action result received. Passing to Data Assistant.")
                    self.import_new_data(action_result)
            return decision
        except Exception as e:
            return self.assistant_error_log("Error in deciding function:", str(e))
    """ CORE FUNCTIONS """
    async def deep_search(self, *search_terms:str) -> List[ToolResult]:
        if not self.is_setup: await self.setup_assistant("\n".join(search_terms))

        recon_step_count = 0
        if not search_terms: await self._get_set_search_terms()
        else: self.search_terms.extend(search_terms)
        search_queue = deque(self.search_terms or [])
        while search_queue:
            term = search_queue.popleft()
            recon_step_count += 1
            self.assistant_log(f"Deep Search step {recon_step_count}")
            self.assistant_log(f"Deep Search term: {term}")
            result = await self.google_search(search_term=term)
            if result and type(result) in [list, tuple]:
                for item in result:
                    item.search_term = term
                self.pending_search_results.extend(result)
            else:
                result.search_term = term
                self.pending_search_results.append(result)
            self.assistant_log(f"Deep Search Step {recon_step_count}")
        return await self._navigate_search_results()
    async def google_search(self, search_term: str) -> ToolResult:
        self.assistant_log("google_search called.")
        url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
        if not url:
            self.assistant_log("Failed: URL was not generated.")
            return ToolResult(error="URL is required for 'navigate' action")
        self.assistant_log(f"Generated URL successfully. URL: [ {url} ]")
        self.assistant_log("Initiating navigation.")
        try:
            result = await self.navigate(url, "search")
            self.assistant_log("Navigation completed successfully.")
            return result
        except Exception as e:
            self.assistant_log(f"Navigation failed: [ {str(e)} ]")
            self.tool_result_log.append(f"Error navigating [ {str(e)} ]")
            return ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url,
                              error=f"Error navigating [ {str(e)} ]")
    async def navigate(self, url: Optional[str], output:Optional[str]='html') -> None | ToolResult | list[ToolResult]:
        self.assistant_log("Navigate called.")
        context = await self.__ensure_browser_initialized()
        self.assistant_log(f"Navigate: Browser initialized: {'Yes' if context else 'No'}")
        if not url:
            self.assistant_log("Navigate: Failed: URL is required but missing.")
            return ToolResult(error="URL is required for 'navigate' action")
        self.assistant_log(f"Navigate: URL validated successfully. URL: [ {url} ]")

        async def handle_dialog(dialog: Dialog) -> None:
            print(f"Dialog detected: {dialog.message}")
            await dialog.dismiss()
            print("Dialog dismissed")
        async def handle_load(page: Page) -> None:
            print(f"WebSocket: Page Loaded: {page.url}")
            html = self.safe_context.get_page_html()
            content = self.__parse_html_to_content(html)
            await self.__generate_report(content, ensure_length=10000)

        try:
            if type(self.page) not in [Page]:
                self.page = await context.get_current_page()
            self.previous_page = self.page
            self.page.once("dialog", handle_dialog)
            self.page.once("load", handle_load)
            self.assistant_log(f"Navigate: Going to page: [ {url} ]")
            await self.page.goto(url, timeout=5000, wait_until="domcontentloaded")

            self.assistant_log("Navigate: Page loaded successfully.")
            html = await context.get_page_html()
            self.assistant_log("Navigate: HTML content retrieved successfully.")

            toolResult = None

            if output == 'pass':
                self.assistant_log("Navigate: Handling pass.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, result="passthrough")

            if output == 'summary':
                self.assistant_log("Navigate: Handling summarized content.")
                toolResult = await self.output_with_summary(url, html)

            elif output == 'search':
                self.assistant_log("Navigate: Handling parsed search results.")
                toolResult = self.output_search_results(html=html)

            elif output == 'html':
                self.assistant_log("Navigate: Handling raw HTML content.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, result=html)

            return toolResult
        except Exception as e:
            self.assistant_log(f"Navigate: Navigation failed: [ {str(e)} ]")
            self.tool_result_log.append(f"Error navigating [ {str(e)} ]")
            return ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url,
                              error=f"Error navigating [ {str(e)} ]")
    async def click(self, index: Optional[int]) -> ToolResult:
        self.assistant_log(f"click called with index: [ {index} ]")
        if index is None:
            self.assistant_log("Click failed: No index provided.")
            return ToolResult(error="Index is required for 'click' action")
        element = await self.context.get_dom_element_by_index(index)
        self.assistant_log(f"Element retrieval: {'Success' if element else 'Failed'}")
        if not element:
            return ToolResult(error=f"Element with index {index} not found")
        download_path = await self.context._click_element_node(element)
        self.assistant_log(f"Element clicked: {'Success' if download_path else 'No download initiated'}")
        output = f"Clicked element at index {index}"
        if download_path:
            output += f" - Downloaded file to {download_path}"
        return ToolResult(output=output)
    async def input_text(self, index: Optional[int], text: Optional[str]) -> ToolResult:
        self.assistant_log("input_text called.")
        if index is None or not text:
            self.assistant_log("Input text failed: Index or text missing.")
            return ToolResult(error="Index and text are required for 'input_text' action")
        element = await self.context.get_dom_element_by_index(index)
        self.assistant_log(f"Element retrieval for input: {'Success' if element else 'Failed'}")
        if not element:
            return ToolResult(error=f"Element with index {index} not found")
        await self.context._input_text_element_node(element, text)
        self.assistant_log("Text input successful.")
        return ToolResult(output=f"Input '{text}' into element at index {index}")
    async def screenshot(self) -> ToolResult:
        self.assistant_log("screenshot called.")
        screenshot = await self.context.take_screenshot(full_page=True)
        self.assistant_log(f"Screenshot captured successfully.")
        return ToolResult(output=f"Screenshot captured (base64 length: {len(screenshot)})", system=screenshot)
    async def refresh_page(self) -> ToolResult:
        self.assistant_log("refresh_page called.")
        await self.context.refresh_page()
        self.assistant_log("Page refreshed successfully.")
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
                return self.tool_results.add_and_pass(tool=tr)
            except Exception as e:
                return ToolResult(error=f"Failed to get browser state: {str(e)}")
    async def go_home(self):
        return await self.navigate("https://www.raico.dev", "summary")
    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.
        Args: new_state: The state to transition to during the context.
        Yields: None: Allows execution within the new state.
        Raises: ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state
    """ Objective/Plan/Steps """
    async def _get_set_objective_async(self):
        result = await self.llm().formatter_async(
            text=self.user_request_prompt,
            model=Objective,
            system=f"""
                **Based on the users request, decide what the objective or goal is to achieve.**
                **What is the end goal?**
            """,
        )

        if result:
            self.overall_objective = result.objective

        return result
    async def _get_set_plan_async(self):
        result = await self.llm().generate_async(
            user=self.user_request_prompt,
            system=f"""
                **You control a web browser interactively.**
                **Based on the objective and the user prompt, develop a plan on how to accomplish the users request/objective.**
                **Ignore requesting for more information, work with what you have, plan can be updated as we go.**

                <TOOLS_AVAILABLE>
                    {self.get_browser_tools()}
                </TOOLS_AVAILABLE>

                <OBJECTIVE>
                    {self.overall_objective}
                </OBJECTIVE>
            """,
        )

        if result:
            self.overall_plan = result

        return result

    #
    async def _get_set_next_step_async(self) -> Optional[NextStepModel]:
        tool_state = await self.get_current_state()
        decisions = ""
        for d in self.decision_log:
            data = DICT.get("function", d, None)
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            temp = f"""
                ----
                Function Name: {func_name}
                Function Arguments: {args_source}
                ----
            """
            decisions += temp
        result = await self.llm().formatter_async(
            text=f"""
                What do we do next to help accomplish the users request/objective to then win the game?
            """,
            model=NextStepModel,
            system=f"""
            **RULES TO THE GAME**
                **YOU CAN ONLY INTERACT WITH 1 SINGLE ELEMENT AT A TIME**
                **YOU CAN ONLY MAKE 1 ACTION WITH THAT 1 SINGLE ELEMENT AT A TIME**
                1. Navigate to a website. (Search for it first if you don't know it, then navigate to it.)
                2. Input Data into Elements for the user according to the DOM Index/Current State.
                3. Click on Elements for the user according to the DOM Index/Current State.
                4. Think about validating a previous step and retrying it according to the DOM Index/Current State.
                **You can only do 1 'Navigate' at a time.**
                **You can only do 1 'Search' at a time.**
                **You can only do 1 'Input' at a time.**
                **You can only do 1 'Click' at a time.**
                *If you want to enter multiple items into input elements, you must pick ONLY 1 input based on the history of steps.
            **CURRENT INFORMATION ON STATE OF THE GAME**
                <ASSISTANT_PROCESS_LOG>
                    {self.get_assistant_log_str() or 'Nothing has happen'}
                </ASSISTANT_PROCESS_LOG>
                <PROCESS_SUMMARY>
                    {self.summary_report or 'Nothing has happen'}
                </PROCESS_SUMMARY>
                <TOOLS_AVAILABLE>
                    {self.get_browser_tools()}
                </TOOLS_AVAILABLE>
                <OBJECTIVE>
                    {self.overall_objective}
                </OBJECTIVE>
                <PLAN>
                    {self.overall_plan}
                </PLAN>
                    {self.initial_request_tagged}
                <PAST_FUNCTION_CALLS>
                    {decisions}
                </PAST_FUNCTION_CALLS>
                <CURRENT_BROWSER_STATE>
                    {tool_state.output}
                </CURRENT_BROWSER_STATE>
                
                **REMEMBER: WE CAN NOT DO 2 THINGS AT ONCE, 1 STEP, 1 ACTION ONLY.**
            """,
        )

        if result:
            self.previous_step = self.current_step
            self.current_step = result or None

        return result or None

    """ DEEP SEARCH MODE """
    async def _navigate_search_results(self, tool_results: List[ToolResult]=None) -> List[ToolResult]:
        recon_step_count = 0
        search_queue = deque(tool_results or self.pending_search_results or [])
        while search_queue:
            search = search_queue.popleft()
            recon_step_count += 1
            self.assistant_log(f"Executing Search Result step {recon_step_count}")
            self.assistant_log(f"Search term: {search.search_term}, Search Url: {search.url}")
            result = await self.navigate(url=search.url, output='summary')
            result.attach_search_parent(search)
            self.assistant_log(f"Extracting Search Result Step {recon_step_count}")
        self.assistant_log("Finished handling Search results.")
        await self.go_home()
        return tool_results
    async def _get_set_search_terms(self) -> Optional[SearchTerms]:
        result = await self.llm().formatter_async(
            text=f"""
                {self.overall_objective}
                **Based on the objective, create a list of at least 10 web search terms to search google with.**
            """,
            model=SearchTerms,
            system=f"""
               **You are a master of creating concise and yet detailed search terms for finding specific objectives and goals**
                    Example: "who hosted the 2025 oscars?"
                    Example: "what is some of the latest geo-political news?"
                    Example: "What are the scores of the latest international soccer games?"
                    Example: "When is the next olympics?"
                <TOOLS_AVAILABLE>
                    {self.map_external_class()}
                </TOOLS_AVAILABLE>
                <OBJECTIVE>
                    {self.overall_objective}
                </OBJECTIVE>
                    {self.initial_request_tagged}
            """,
        )

        if result:
            self.assistant_log(f"Search terms for {self.overall_objective}\n {str(result.search_terms)}")
            self.search_terms.extend(result.search_terms)
        return result or None

if __name__ == "__main__":

    looper = asyncio.get_event_loop()
    # looper.run_until_complete(BrowserTool().run(request="Who were the last international soccer teams to play, who played and what were the scores?"))
    looper.run_until_complete(BrowserTool().self_navigation("go to facebook, login, search for mallory romeo, go to her profile"))
