import asyncio
import json
from collections import deque
from typing import Optional, Type, Any, List, Union
from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from browser_use.dom.views import DOMTextNode, DOMBaseNode, DOMElementNode
from browser_use.utils import time_execution_sync
from bs4 import BeautifulSoup
from playwright.async_api import Page, Dialog
from pydantic import Field, BaseModel
from rai.agentic.aether.UseBrowserConfig import config
from rai.agentic.agent_tools.base import BrowserToolState
from rai.agentic.agent_tools.engine import ToolEngine
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.ai_plugins.reason import SearchTerms
from rai.agentic.ai_tools.text_tools.text_formats import InteractiveElements
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

class WebBrowserTool(ToolEngine):

    @staticmethod
    def module_name() -> str: return 'The Web Browser Assistant'
    @staticmethod
    def tool_assistant_name() -> str: return "Web Browser Assistant"
    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You control a web browser by Matching Index Numbers to their corresponding Names/Details.
            You take in a request, develop a plan and accomplish the task.
            1. Always close/cancel/dismiss popups or dialogs.
        """
    @staticmethod
    def ToolState() -> Type[BrowserToolState]: return BrowserToolState

    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION

    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)

    page: Optional[Page] = None
    previous_page: Optional[Page] = None
    current_page: Optional[Page] = None

    """ PUB/SUB STREAMING OUTPUT """
    pub = IORedis
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

    """ OUTPUT """
    async def output_search_results(self, html: str) -> ToolResult:
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
            temp = f"""
                search_url={url},
                search_description={description},
                search_title={title},
            """
            results.append(temp)
        summary = await self.get_content(html=html, summarize=True)
        r = "\n".join(results)
        return ToolResult(
            result_type="search",
            result_status="ready",
            output=summary+r,
        )
    async def get_content(self, html:str, summarize:bool=True) -> str:
        body = await WebBodyExtractor.pipeline_async(html)
        content = self.TEXT_CLEANER(body.combined_text)
        if summarize: content = await self.ask_role_master_to_summarize(content)
        return content
    async def output_with_summary(self, url, html) -> ToolResult:
        body = await WebBodyExtractor.pipeline_async(html)
        content = TextProcessor.TEXT_CLEANER(body.combined_text)
        if not TextProcessor.string_length_is_within(content, 100):
            content = await self.ask_role_master_to_understand(f"WebPage Url: [{url}]\n{content}")
        return ToolResult(
            output=f"BrowserTool: Navigated to [ {url} ]",
            result_type="search",
            action="search google",
            url=url,
            result=content
        )

    """ CONTEXT/STATE """
    @property
    def safe_context(self) -> Optional[BrowserContext]:
        if type(self.context) in [BrowserContext]: return self.context
        return None
    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool(function_name="google_search"),
            self.get_tool(function_name="navigate_to_url"),
            self.get_tool(function_name="click"),
            self.get_tool(function_name="input_text"),
            self.get_tool(function_name="scroll"),
            self.get_tool(function_name="press_enter"),
            self.get_tool(function_name="ask_agent_a_question"),
            self.get_tool(function_name="finish")
        ]
    async def ensure_browser_initialized(self) -> Optional[BrowserContext]:
        """Ensure browser and context are initialized."""

        if type(self.context) in [BrowserContext]: return self.context
        # await self.pub.connect()
        # await self.start_screenshot_stream()

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

    async def inject_dom_interactions(self) -> ToolResult:
        state = await self.context.get_state()
        # indexed_interactions = state.element_tree.clickable_elements_to_string()
        sel_map = state.selector_map

        result = []
        a_tags = []
        input_tags = []
        btn_tags = []
        other_tags = []
        for k,v in sel_map.items():
            index = k
            element = v
            stringed_element = self.__clickable_elements_to_str(element)
            if str(element).startswith('<a'):
                a_tags.append(stringed_element)
            elif str(element).startswith('<button'):
                btn_tags.append(stringed_element)
            elif str(element).startswith('<input') or str(element).startswith('<select'):
                input_tags.append(stringed_element)
            else:
                other_tags.append(stringed_element)
            # if index >= 100: continue
            # result.append(stringed_element)
            print(index, stringed_element)

        result.extend(input_tags)
        result.extend(btn_tags)
        result.extend(a_tags)
        # result.extend(other_tags)
        return ToolResult(
            result="\n".join(result),
        )
    @time_execution_sync('--clickable_elements_to_string')
    def __clickable_elements_to_str(self, element, include_attributes: list[str] = []) -> str:
        """Convert the processed DOM content to a human-readable string,
        returning only relevant interactive elements."""
        formatted_text = []

        def process_parent(node: DOMBaseNode, depth: int) -> Union[str | None]:
            if depth >= 10: return None
            if node.parent:
                p = node.parent
                attrs = p.attributes
                if not attrs: return process_parent(p, depth + 1)
                return process_node(node, 0)


        def process_node(node: DOMBaseNode, depth: int) -> None:
            indent = '  ' * depth  # Indentation reflects DOM hierarchy
            try:
                if isinstance(node, DOMElementNode):
                    # Process only interactive elements with a highlight_index.
                    if node.is_interactive and node.highlight_index is not None:

                        # parent_attrs = process_parent(node, 0)

                        # Combine requested attributes with additional contextual keys.
                        extra_keys = ['id', 'class', 'aria-label', 'role', 'placeholder']
                        all_keys = set(include_attributes) | set(extra_keys)
                        attributes_list = []
                        for key in all_keys:
                            if key in node.attributes:
                                attr_value = node.attributes[key]
                                # Avoid including redundant data if the attribute value equals the tag name.
                                if attr_value != node.tag_name:
                                    attributes_list.append(f'{key}="{attr_value}"')
                        attributes_str = ' '.join(attributes_list)

                        # Extract associated text; for input-like elements, fallback to the 'value' attribute.
                        text = node.get_all_text_till_next_clickable_element()
                        # if str(text) == '': return None
                        if not text and node.tag_name.lower() in ['input', 'button']:
                            text = node.attributes.get('value', '')

                        # Append viewport and coordinate details if available.
                        viewport_info = ''
                        if node.viewport_coordinates:
                            viewport_info += f' [viewport: {node.viewport_coordinates}]'
                        if node.page_coordinates:
                            viewport_info += f' [page: {node.page_coordinates}]'
                        if node.is_in_viewport:
                            viewport_info += ' [visible]'
                        if node.is_interactive:
                            viewport_info += ' [is_interactive]'
                        if node.is_top_element:
                            viewport_info += ' [is_top_element]'
                        # if parent_attrs:
                        #     viewport_info += f' [{parent_attrs}]'

                        # Format the line with indentation, highlight index, tag name, attributes, text, and viewport info.
                        line = f"{indent}[{node.highlight_index}] <{node.tag_name}"
                        if attributes_str:
                            line += f" {attributes_str}"
                        if text:
                            line += f"> {text}"
                        else:
                            line += ">"
                        line += f"/>{viewport_info}"
                        formatted_text.append(line)

                    # Process children regardless of the current node's interactivity.
                    for child in node.children:
                        process_node(child, depth + 1)

                # Skip processing DOMTextNode, as we're focused solely on interactive elements.
            except Exception as e:
                # In production, consider logging the error.
                formatted_text.append(f"{indent}[Error processing node: {e}]")

        process_node(element, 0)
        return '\n'.join(formatted_text)
    async def get_current_state(self) -> ToolResult:
        """Get the current browser state as a ToolResult."""
        async with self.lock:
            try:
                context = await self.ensure_browser_initialized()
                state = await context.get_state()
                state_info = {
                    "url": state.url,
                    "title": state.title,
                    "tabs": [tab.model_dump() for tab in state.tabs],
                    # "interactive_elements": state.element_tree.clickable_elements_to_string(),
                }
                tr = ToolResult(
                    output=str(json.dumps(state_info)),
                    result_type="tool_state"
                )
                interactions: ToolResult = await self.inject_dom_interactions()
                tri = interactions.merge(tr)
                tri.success = True
                return self.add_and_pass(tool_or_tools=tri)
            except Exception as e:
                return self.add_and_pass(tool_or_tools=ToolResult(
                    success=False,
                    error=f"Failed to get browser state: {str(e)}")
                )

    """ CORE FUNCTIONS """
    def finish(self, message:str): return self.quit()
    def ask_agent_a_question(self, question:str): return self.ask_role_master_a_question(question)
    # Search
    async def _deep_search(self, *search_terms:str) -> List[ToolResult]:
        if not self.is_setup:
            await self.setup_assistant("\n".join(search_terms))

        recon_step_count = 0
        if search_terms: await self.think_then_set_search_terms()
        self.find_all_search_results()
        search_queue = self.tool_plan.search_term_queue or deque(search_terms)
        while search_queue:
            term = search_queue.popleft()
            recon_step_count += 1
            self.log_voice(f"Deep Search step {recon_step_count}")
            self.log_voice(f"Deep Search term: {term}")
            result = await self.google_search(search_term=term)
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
        return await self.navigate_through_search_results()
    async def google_search(self, search_term: str) -> ToolResult:
        self.log_voice(f"I am going to search google for: {search_term}")
        url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
        if not url:
            self.log_voice("Failed: URL was not generated.")
            return ToolResult(error="URL is required for 'navigate' action")
        try:
            result = await self._navigate(url, "search")
            self.log_voice("Navigation completed successfully.")
            return self.add_and_pass(result)
        except Exception as e:
            self.log_voice(f"Navigation failed: [ {str(e)} ]")
            self.log_thought(f"Error navigating [ {str(e)} ]")
            return self.add_and_pass(ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", url=url, error=f"Error navigating [ {str(e)} ]"))
    # Navigation Controls
    async def navigate_to_url(self, url: Optional[str]) -> None | ToolResult | list[ToolResult]:
        return await self._navigate(url, "summary")
    async def _navigate(self, url: Optional[str], output:Optional[str]= 'summary') -> None | ToolResult | list[ToolResult]:
        self.log_voice(f"I am going to navigate to [ {url} ]")
        context = await self.ensure_browser_initialized()
        if not url:
            self.log_voice("Umm, I dont seem to see a URL...")
            return ToolResult(error="URL is required for 'navigate' action")
        self.log_voice(f"Navigate: URL validated successfully. URL: [ {url} ]")

        async def handle_dialog(dialog: Dialog) -> None:
            print(f"Dialog detected: {dialog.message}")
            await dialog.dismiss()
            print("Dialog dismissed")
        async def handle_load(page: Page) -> None:
            print(f"WebSocket: Page Loaded: {page.url}")
            html = await self.safe_context.get_page_html()
            content = await self.html_to_content(html)
            await self.ask_role_master_for_a_summary_report(content, ensure_length=10000)

        try:
            if type(self.page) not in [Page]: self.page = await context.get_current_page()
            self.previous_page = self.page
            self.page.once("dialog", handle_dialog)
            self.page.once("load", handle_load)
            self.log_voice(f"Navigate: Going to page: [ {url} ]")
            await self.page.goto(url, timeout=5000, wait_until="domcontentloaded")
            self.log_voice("I have successfully loaded the page.")

            toolResult = None
            html = await context.get_page_html()
            if output == 'page':
                self.log_voice("The requested output is the page object itself.")
                page = await context.get_current_page()
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", holding="page", holder=page)

            elif output == 'pass':
                self.log_voice("I am passing the request. Viewing only it would appear.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", result="passthrough")

            elif output == 'summary':
                self.log_voice("I am generating a summary of the page.")
                toolResult = await self.output_with_summary(url, html)

            elif output == 'search':
                self.log_voice("Navigate: Handling parsed search results.")
                toolResult = await self.output_search_results(html=html)
                toolResult.url = url

            elif output == 'html':
                self.log_voice("Navigate: Handling raw HTML content.")
                toolResult = ToolResult(output=f"BrowserTool: Navigated to [ {url} ]", result=html)

            content = await self.get_content(html=html, summarize=False)
            await self.ask_role_master_for_a_summary_report(content)
            toolResult.success = True
            return toolResult
        except Exception as e:
            self.log_voice(f"Navigate: Navigation failed: [ {str(e)} ]")
            self.log_thought(f"Error navigating [ {str(e)} ]")
            return ToolResult(
                success=False,
                output=f"BrowserTool: Navigated to [ {url} ]",
                url=url,
                error=f"Error navigating [ {str(e)} ]"
            )
    async def click(self, index: Optional[int]) -> ToolResult:
        self.log_voice(f"click called with index: [ {index} ]")
        try:
            if index is None:
                self.log_voice("Click failed: No index provided.")
                return ToolResult(success=False, error="Index is required for 'click' action")
            element = await self.context.get_dom_element_by_index(index)
            self.log_voice(f"Element retrieval: {'Success' if element else 'Failed'}")
            if not element:
                return ToolResult(success=False, error=f"Element with index {index} not found")
            download_path = await self.context._click_element_node(element)
            self.log_voice(f"Element clicked: {'Success' if download_path else 'No download initiated'}")
            output = f"Clicked element at index {index}"
            if download_path:
                output += f" - Downloaded file to {download_path}"
            return ToolResult(
                success=True,
                output=output)
        except Exception as e:
            self.log_voice(f"Click element failed: [ {str(e)} ]")
            return ToolResult(success=False, error=f"Click element failed: [ {str(e)} ]")
    async def input_text(self, index: Optional[int], text: Optional[str]) -> ToolResult:
        self.log_voice("input_text called.")
        try:
            if index is None or not text:
                self.log_voice("Input text failed: Index or text missing.")
                return ToolResult(success=False, error="Index and text are required for 'input_text' action")
            element = await self.context.get_dom_element_by_index(index)
            self.log_voice(f"Element retrieval for input: {'Success' if element else 'Failed'}")
            if not element:
                return ToolResult(success=False, error=f"Element with index {index} not found")
            print(element.is_in_viewport)
            print(element.viewport_info)
            await self.context._input_text_element_node(element, text)
            self.log_voice("Text input successful.")
            return ToolResult(success=True, output=f"Input '{text}' into element at index {index}")
        except Exception as e:
            self.log_voice(f"Input text failed: [ {str(e)} ]")
            return ToolResult(success=False, error=f"Input text failed: [ {str(e)} ]")
    async def press_enter(self) -> ToolResult:
        self.log_voice(f"I am going to press enter.")
        await self.page.keyboard.press("Enter")
        self.log_voice("I have pressed enter.")
        return ToolResult(success=True, output=f"Pressed enter key.")
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
    async def execute_js(self, script: Optional[str]) -> ToolResult:
        if not script:
            return ToolResult(error="Script is required for 'execute_js' action")
        result = await self.context.execute_javascript(script)
        return ToolResult(output=str(result))
    async def scroll(self, scroll_amount: Optional[int]) -> ToolResult:
        if scroll_amount is None:
            return ToolResult(success=False, error="Scroll amount is required for 'scroll' action")
        await self.context.execute_javascript(f"window.scrollBy(0, {scroll_amount});")
        direction = "down" if scroll_amount > 0 else "up"
        return ToolResult(success=True, output=f"Scrolled {direction} by {abs(scroll_amount)} pixels")
    async def go_home(self) -> ToolResult:
        return await self._navigate(url="https://www.raico.dev", output="page")

    # Page Extraction
    async def get_html(self) -> ToolResult:
        html = await self.context.get_page_html()
        truncated = html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
        return ToolResult(success=True, output=truncated)
    async def get_text(self) -> ToolResult:
        text = await self.context.execute_javascript("document.body.innerText")
        print("BrowserUseTool: get_text: ", text)
        return ToolResult(success=True, output=text)
    async def read_links(self) -> ToolResult:
        links = await self.context.execute_javascript(
            "document.querySelectorAll('a[href]').forEach((elem) => {if (elem.innerText) {console.log(elem.innerText, elem.href)}})"
        )
        return ToolResult(success=True, output=links)

    # Browser Controls
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

    """ DEEP SEARCH MODE """
    async def navigate_through_search_results(self, tool_results: List[ToolResult]=None) -> List[ToolResult]:
        recon_step_count = 0
        search_queue = deque(tool_results or self.find_all_search_results() or [])
        while search_queue:
            search = search_queue.popleft()
            recon_step_count += 1
            self.log_voice(f"Executing Search Result step {recon_step_count}")
            self.log_voice(f"Search term: {search.search_term}, Search Url: {search.url}")
            result = await self._navigate(url=search.search_url, output='summary')
            result.attach_search_parent(search)
            self.log_voice(f"Extracting Search Result Step {recon_step_count}")
        self.log_voice("Finished handling Search results.")
        await self.go_home()
        return tool_results
    async def think_then_set_search_terms(self) -> Optional[SearchTerms]:
        result = await self.llm().formatter_async(
            text=f"""
                {self.inject_core_objective_tag()}
                **Based on the objective, create a list of at least 10 web search terms to search google with.**
            """,
            model=SearchTerms,
            system=f"""
               **You are a master of creating concise and yet detailed search terms for finding specific objectives and goals**
                    Example: "who hosted the 2025 oscars?"
                    Example: "what is some of the latest geo-political news?"
                    Example: "What are the scores of the latest international soccer games?"
                    Example: "When is the next olympics?"
                {self.inject_tool_options_tag()}
                {self.inject_core_objective_tag}
                {self.inject_core_user_request_tag()}
            """,
        )

        if result:
            self.log_voice(f"Search terms for {self.tool_plan.overall_objective}\n {str(result.search_terms)}")
            self.tool_plan.search_term_queue.extend(result.search_terms)
        return result or None

if __name__ == "__main__":

    looper = asyncio.get_event_loop()
    #looper.run_until_complete(WebBrowserTool().self_navigation("go to dominoes and order me a single large pepperoni pizza, my address is 801 6th avenue southwest, alabaster, AL 35007, then order the pizza and have it delivered to my house."))
    looper.run_until_complete(WebBrowserTool().self_navigation("I want you to order pizza on dominoes that will be for pick-up and set the time of pick-up to be 5:45pm. My dominoes is alabaster, AL 35007. I want a large pepperoni pizza with light sauce. I also want a medium cheese pizza. I want you to order this pizza for me now."))
    # looper.run_until_complete(WebBrowserTool().self_navigation("What is bruce romeos law firm called? I know he left mezrano, so that is not it."))
