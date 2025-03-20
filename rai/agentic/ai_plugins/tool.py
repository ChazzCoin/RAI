import asyncio
import inspect
import json
import uuid
from abc import ABC, abstractmethod
from collections import deque
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict

from F import DICT
from bs4 import BeautifulSoup
from pydantic import BaseModel

from rai.agentic.aether.schema import AgentState
from rai.agentic.aether.tool import ToolResult
from rai.agentic.ai_modules import mAssistLog, ToolLog
from rai.agentic.ai_modules.data import mData
from rai.agentic.ai_modules.map import mMap
from rai.agentic.ai_modules.r import rModule
from rai.agentic.ai_plugins.reason import Objectives, Objective
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor


class ToolPlan(BaseModel):
    mode: str = "next-step"
    initial_request: str = ""
    user_data: Optional[Dict[str, str]] = None
    role: str = "**You control a web browser interactively.**"
    user_request: str = ""
    objectives: Objectives = Objectives()
    overall_objective: str = "Unknown Objective"
    overall_plan: str = "Unknown Plan"

    actions: List[dict[str, Any]] = []
    decisions_made: List[str] = []

    step_queue: deque[NextStepModel] = deque([])
    overflow_step_queue: List[NextStepModel] = []
    steps_taken: List[NextStepModel] = []
    previous_step: Optional[NextStepModel] = None
    current_step: Optional[NextStepModel] = None

    required_data: Optional[Dict[str, str]] = None
    max_steps: int = 10
    current_step_count: int = 0

    current_state: ToolResult = ToolResult()

    def inject_user_request(self) -> str:
        return f"""
               <USER_REQUEST>
                   {self.user_request}
               </USER_REQUEST>
           """
    def inject_decisions_prompt(self) -> str:
        decisions = ""
        for d in self.decisions_made:
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
        temp = f"""
            <PAST_FUNCTION_CALLS>
                {decisions}
            </PAST_FUNCTION_CALLS>
        """
        return temp
    def inject_objective_prompt(self) -> str:
        return f"""
            <OBJECTIVE>
                {self.overall_objective}
            </OBJECTIVE>
        """
    def inject_plan_prompt(self) -> str:
        return f"""
            <PLAN>
                {self.overall_plan}
            </PLAN>
        """
    def inject_contextual_prompt(self) -> str:
        return f"""
            **OBJECTIVE CONTEXT FOR SUMMARIZATION = {self.overall_objective}
            **PLAN CONTEXT FOR SUMMARIZATION = {self.overall_plan}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.initial_request}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """
    def inject_role_prompt(self) -> str:
        return f"""
            <ROLE>
                {self.role}
            </ROLE>
        """

class ToolManager(ToolLog):
    def log_key(self) -> str:
        return "tool"

    name: Optional[str] = None
    tool_id: str = str(uuid.uuid4())
    tool_plan: ToolPlan = ToolPlan()
    tool_results: List['ToolResult'] = []

    summary_report: str = "Nothing has happen"
    def inject_summary_report_prompt(self) -> str:
        return f"""
            <PROCESS_SUMMARY>
                {self.summary_report}
            </PROCESS_SUMMARY>
        """

    soup = lambda html: BeautifulSoup(html, 'html.parser')

    @property
    def steps(self) -> deque[NextStepModel]:
        return self.tool_plan.step_queue
    def add_step(self, step: NextStepModel):
        if not step: return
        if type(step) not in [NextStepModel]: return

        if not self.maxStepsHasNotBeenMet:
            self.log_thought("Max Steps have been met, the main queue is closed.")
            self.log_thought("I am adding the requested step to the overflow queue.")
            self.tool_plan.overflow_step_queue.append(step)
            return

        self.log_thought("I am adding the new step to our step queue.")
        self.tool_plan.step_queue.append(step)
    def pop_next_step(self) -> NextStepModel:
        self.log_thought("I am grabbing the next step from our step queue.")
        return self.tool_plan.step_queue.popleft()
    def pop_oldest_step(self) -> NextStepModel:
        self.log_thought("I am grabbing the oldest step from our step queue.")
        return self.tool_plan.step_queue.pop()
    @property
    def maxStepsHasNotBeenMet(self) -> bool:
        return self.tool_plan.current_step_count < self.tool_plan.max_steps
    def step_queue_is_empty(self) -> bool:
        return len(self.tool_plan.step_queue) == 0
    def add_step_taken(self, step: NextStepModel):
        self.log_thought("I am adding the last step taken to the step archive.")
        self.tool_plan.steps_taken.append(step)


    def add_user_request(self, request:str):
        self.log_thought(f"The user has given me a request to accomplish for them: {request}")
        self.tool_plan.initial_request = request
    def get_decisions_made(self):
        return self.tool_plan.decisions_made
    def add_decision(self, decision:str):
        self.log_thought(f"I have made the decision: {decision}")
        self.tool_plan.decisions_made.append(decision)
    def set_objective(self, objective:str):
        self.log_thought(f"I have decided on the overall objective: {objective}")
        self.tool_plan.overall_objective = objective
    def set_plan(self, plan:str):
        self.log_thought(f"I have decided on the overall plan: {plan}")
        self.tool_plan.overall_plan = plan

    def add_results(self, tools: List['ToolResult']):
        self.log_thought(f"I have gathered [ {len(tools)} ] results.")
        self.tool_results.extend(tools)
    def add_result(self, tool: 'ToolResult'):
        self.log_thought(f"I have gathered 1 result: {tool.output}")
        self.tool_results.append(tool)
    def add_and_pass(self, tool: 'ToolResult') -> 'ToolResult':
        if tool.result_type == "tool_state":
            self.log_thought(f"I am getting a new current state update: {tool.result}")
            self.tool_plan.current_state = tool
        self.log_thought(f"I have gathered the results: {tool.output}")
        self.tool_results.append(tool)
        return tool
    def count_results(self) -> int:
        items = len(self.tool_results)
        self.log_thought(f"We have gathered [ {items} ] from our actions.")
        return items
    def to_str(self) -> str: return "\n".join([item.to_str() for item in self.tool_results])
    def order_by_timestamp(self, descending: bool = False):
        self.tool_results.sort(key=lambda x: x.timestamp, reverse=descending)
    def get_oldest(self) -> Optional['ToolResult']:
        return min(self.tool_results, key=lambda x: x.timestamp, default=None)
    def get_newest(self) -> Optional['ToolResult']:
        return max(self.tool_results, key=lambda x: x.timestamp, default=None)
    def find_all_equals(self, attribute: str, value: Any) -> List['ToolResult']:
        return [item for item in self.tool_results if getattr(item, attribute, None) == value]
    def find_all_search_results(self) -> List['ToolResult']:
        return [item for item in self.tool_results if getattr(item, "result_type", None) == "search"]
    def find_all_pending_search_results(self) -> List['ToolResult']:
        return [item for item in self.tool_results if getattr(item, "result_type", None) == "search" and getattr(item, "result_status", None) == "complete"]

    """
    - validate 'the next step' is only 1 step and if not, break it out into multiple steps..
    - ask an ai to review the tools state and history to see if it needs help...
    - we need a step validator... did the step succeed or fail? retry or new idea?

    """
class ToolEngine(rModule, mMap, mData, ToolManager, TextProcessor, ABC):
    is_setup: bool = False
    state: AgentState = AgentState.IDLE
    tool_state: ToolResult = ToolResult()
    lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    @abstractmethod
    def tool_assistant_name() -> str:
        """Return the assistant rules as a string."""
        pass
    @staticmethod
    @abstractmethod
    def assistant_rules() -> str:
        """Return the assistant rules as a string."""
        pass
    @abstractmethod
    def get_tools(self) -> List[dict[str, Any]]:
        """Return the assistants tool options."""
        pass
    """ Setup Assistant """
    """ ASSISTANT """
    async def self_navigation(self, request: Optional[str] = None) -> str:
        await self.setup_assistant(user_request=request)
        async with self.state_context(AgentState.RUNNING):
            while self.stepQueueIsLive():
                step = self.pop_next_step()
                self.tool_plan.current_step_count += 1
                self.log_voice(f"Executing step {self.tool_plan.current_step_count}/{self.tool_plan.max_steps}")
                await self.think_then_decide_and_act(step)
                self.add_step_taken(step)
                self.log_voice(f"Step {self.tool_plan.current_step_count} Finished")
                await self.think_about_next_step()
            if not self.maxStepsHasNotBeenMet:
                self.tool_plan.current_step_count = 0
                self.state = AgentState.IDLE
                self.log_voice(f"Terminated: Reached max steps ({self.tool_plan.max_steps})")

        return await self.think_then_respond()

    async def setup_assistant(self, user_request: str):
        # The Assistant Process Log
        self.state = AgentState.RUNNING
        self.log_voice(f"HELLO! I am {self.tool_assistant_name()}! Let's get started!")
        self.log_voice("Hang Tight. I'm gathering your initial request the rules, documentation and data.")
        self.tool_plan.user_request = user_request
        await self.think_then_set_objective()
        await self.think_then_set_plan()
        await self.think_about_next_step()
        self.log_voice("Okay, I have the objective, plan and next step put together. Let's get started!")
    """ Helpers """
    def stepQueueIsLive(self) -> bool:
        return self.maxStepsHasNotBeenMet and self.state != AgentState.FINISHED
    @staticmethod
    async def html_to_content(html):
        body = await WebBodyExtractor.pipeline_async(html)
        return TextProcessor.TEXT_CLEANER(body.combined_text)

    @abstractmethod
    async def get_current_state(self) -> ToolResult:
        """Get the current browser state as a ToolResult."""
        pass
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
    async def think_then_decide_and_act(self, step: NextStepModel) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tool_state = await self.get_current_state()
            nav_prompt = f"""
                Review the following web html DOM index interactive elements.
                Based on the User Prompt, pick the index and tool function accordingly.
                    {self.inject_voice_prompt() or 'We havent said anything'}
                    {self.inject_thoughts_prompt() or 'We havent thought about anything.'}
                    {self.inject_summary_report_prompt()}
                    {self.tool_plan.inject_decisions_prompt()}
                <CURRENT_BROWSER_STATE>
                    {tool_state.output}
                </CURRENT_BROWSER_STATE>
            """
            step_prompt = f"""
                <USER_DATA>
                    Username/Email: 
                    Password: 
                </USER_DATA>
                <NEXT_STEP_TO_ACHIEVE>
                    {step.next_step_or_action}
                </NEXT_STEP_TO_ACHIEVE>
            """
            self.log_voice("I am trying to decide which action to make next.")
            decision = await self.llm().generate_function_async(
                user=step_prompt,
                system=nav_prompt,
                functions=self.get_tools(),
                raw_result=True
            )

            if decision:
                self.add_decision(decision)
                action_result = await self.parse_and_call_function_async(decision)
                self.add_step_taken(step)
                if action_result:
                    self.log_voice(f"I have received the action result received. Passing to Data Assistant.")
                    self.import_new_data(action_result)
            return decision
        except Exception as e:
            self.log_thought(f"An error occurred while trying to decide: {e}")
            return self.log_voice("I am having trouble making a decision.")
    async def think_then_set_objective(self):
        self.log_voice("I need to understand the users objective. What is their end goal?")
        result = await self.think.formatter_async(
            text=self.tool_plan.inject_user_request(),
            model=Objective,
            system=self.inject_objective_system_prompt(),
        )
        self.log_voice("Okay, I think I understand the objective.")
        if result: self.tool_plan.overall_objective = result.objective
        return result
    async def think_then_set_plan(self):
        result = await self.llm().generate_async(
            user=self.tool_plan.user_request,
            system=f"""
                **You control a web browser interactively.**
                **Based on the objective and the user prompt, develop a plan on how to accomplish the users request/objective.**
                **Ignore requesting for more information, work with what you have, plan can be updated as we go.**

                <TOOLS_AVAILABLE>
                    {self.get_external_json_tools()}
                </TOOLS_AVAILABLE>

                {self.tool_plan.inject_objective_prompt()}
            """,
        )

        if result:
            self.tool_plan.overall_plan = result

        return result
    async def think_about_next_step(self, depth=0) -> Optional[NextStepModel]:
        result = await self.think.formatter_async(
            text=self.inject_next_step_user_prompt(),
            model=NextStepModel,
            system=self.inject_next_step_system_prompt(),
        )
        if result:
            self.add_step(result)
            self.tool_plan.previous_step = self.tool_plan.current_step
            self.tool_plan.current_step = result or None
        elif depth >= 3: return await self.think_about_next_step(depth=(depth + 1))
        return result or None
    async def think_then_summarize(self, content, ensure_length:int = 10000):
        content = self.ensure_within_limit(content, ensure_length)
        return self.llm().generate(user=content, system=f"""
            Read and Analyze this HTML based extracted content from a website page.
            **REMOVE all web/html specific information**
            **CONTEXT FOR SUMMARIZATION = {self.tool_plan.overall_objective}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.tool_plan.user_request}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """)
    async def think_then_summary_report(self, content, ensure_length:int = 10000) -> str:
        self.log_voice("I am condensing my research to help me remember it better.")
        if self.summary_report == "":
            report = await self.think_then_summarize(content, ensure_length)
            if report:
                self.summary_report = report
                return report

        content = self.ensure_within_limit(content, ensure_length)
        prompt = f"""
            {self.inject_summary_report_prompt()}
            <NEW_CONTENT_TO_ADD_TO_SUMMARY>
                {content}
            </NEW_CONTENT_TO_ADD_TO_SUMMARY>
        """
        report = await self.llm().generate_async(user=prompt, system=self.inject_summary_report_system_prompt())
        if report and str(report) != "":
            self.log_voice(f"I've updated my memory summary:\n{report}")
            self.summary_report = report
        return report
    async def think_about_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.log_voice("Umm, what should I tell the user?")
            final_response_request = self.chain_data(
                self.tool_plan.inject_objective_prompt(),
                self.get_thoughts(),
                self.summary_report,
                self.tool_plan.inject_user_request(),
            )
            response = self.llm().generate(
                user=final_response_request,
                system="Based on the data provided, create the appropriate response to send back to the user."
            )
            self.log_voice("I have come up with a response for you.")
            self.log_voice(response)
            return response
        except Exception as e:
            return self.add_problem(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")

    async def think_then_respond(self) -> 'AssistResponse':
        final_response = await self.think_about_response()
        return self.AssistResponse(
            prefix="",
            session_id="",
            answer=final_response,
            data=self.get_data()
        )

    """ Prompts """
    def inject_tool_state_prompt(self):
        return f"""
            <CURRENT_BROWSER_STATE>
                {self.tool_state.output}
            </CURRENT_BROWSER_STATE>
        """
    def inject_tool_options_prompt(self):
        return f"""
            <TOOLS_AVAILABLE>
                {self.get_external_json_tools()}
            </TOOLS_AVAILABLE>
        """
    def inject_summary_report_prompt(self):
        return f"""
            <PROCESS_SUMMARY>
                {self.summary_report or 'Nothing has happen'}
            </PROCESS_SUMMARY>
        """
    def inject_summary_report_system_prompt(self):
        return f"""
            **You keep and update an on-going summary of content you've read.**
            You are to creating an on-going summary or timeline of reading results.
            You will 'merge' the results together into 1 single memory timeline.
            **CONTEXT FOR SUMMARIZATION = {self.tool_plan.overall_objective}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.tool_plan.user_request}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """
    def inject_next_step_user_prompt(self):
        return f"What do we do next to help accomplish the users request/objective to then win the game?"
    def inject_next_step_system_prompt(self):
        return f"""
            **RULES TO THE GAME**
                **YOU CAN ONLY CALL ONE SINGLE FUNCTION AT A TIME.**
                1. Review the past log of steps taken.
                2. Review the Users Request, Overall Objective and Overall Plan.
                3. Review the current state you are in.
                4. Think about validating a previous step and retrying it according to the Current State.
                **You can only do 1 'action' at a time.**
                **You can only call 1 function at a time.**
                **Pretend you are trying to explain to a 5 year how to do the next single action.**
            **CURRENT INFORMATION ON STATE OF THE GAME**
                    {self.inject_thoughts_prompt()}
                    {self.inject_summary_report_prompt()}
                    {self.inject_tool_options_prompt()}
                    {self.tool_plan.inject_objective_prompt()}  
                    {self.tool_plan.inject_plan_prompt()}  
                    {self.tool_plan.inject_user_request()}
                    {self.tool_plan.inject_decisions_prompt()}  
                    {self.inject_tool_state_prompt()}
                **REMEMBER: WE CAN NOT DO 2 THINGS AT ONCE, 1 STEP, 1 ACTION ONLY.**
            """
    def inject_objective_system_prompt(self):
        return f"""
            **Based on the users request, decide what the objective or goal is to achieve.**
            **What is the end goal?**
        """