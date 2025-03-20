
import asyncio
import json
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional, Any
from rai.agentic.aether.schema import AgentState
from rai.agentic.agent_tools.manager import ToolManager
from rai.agentic.agent_tools.module import ToolModule
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.agent_tools.data import ToolData
from rai.agentic.ai_modules.map import mMap
from rai.agentic.ai_plugins.reason import Objective
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel
from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor

class ToolEngine(ToolModule, ToolData, ToolManager, mMap, ABC):

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
        """Return the assistants tool options.

        MODES:
            1. Running
            2. Idle
            3. Error
            4. Safe
            5. Output

        The mode will dictate which 'tools' the engine gets access to and is able to call.
        """
        pass

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
    async def html_to_content(self, html):
        body = await WebBodyExtractor.pipeline_async(html)
        return self.TEXT_CLEANER(body.combined_text)
    @abstractmethod
    async def get_current_state(self) -> ToolResult: pass
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

    """ Thinking 
    1. Generate a role
    2. 'Split' out each step into potentially multiple steps
    3. Ask to review the tools state and history to see if it needs help...
    4. Summarize Previous Action Result
    5. Review the last N steps and decide if we need to re-adjust.
    6. Analyze the provided 'tools' and create an 'action list' the next step creator has to pick from.
    7. Create a Required Data Checklist.
    8. Validate Each Action, adjust accordingly. did the step succeed or fail? retry or new idea?
    """
    # THINK: The Overall Assistant Identity
    async def think_then_set_objective(self, depth=0):
        self.log_voice("I need to understand the users objective. What is their end goal?")
        result = await self.think.formatter_async(
            text=self.inject_user_request_tag(),
            model=Objective,
            system=self.prompt_objective_system(),
        )
        self.log_voice("Okay, I think I understand the objective.")
        if result:
            try:
                self.tool_plan.overall_objective = result
            except Exception as e:
                self.log_thought(f"An error occurred while trying to overall objective: {e}")
                try:
                    result = json.dumps(result)
                    self.tool_plan.overall_objective = result
                except Exception as e:
                    self.log_thought(f"An error occurred while trying to overall objective: {e}")
                    if depth >= 3: return await self.think_then_set_objective(depth=depth+1)
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

                {self.inject_objective_tag()}
            """,
        )

        if result:
            self.tool_plan.overall_plan = result

        return result
    # ACT: On-The-Fly Actions
    async def think_about_next_step(self, depth=0) -> Optional[NextStepModel]:
        result = await self.think.formatter_async(
            text=self.prompt_next_step_user(),
            model=NextStepModel,
            system=self.prompt_next_step_system(),
        )
        if result:
            self.add_step(result)
            self.tool_plan.previous_step = self.tool_plan.current_step
            self.tool_plan.current_step = result or None
        elif depth >= 3: return await self.think_about_next_step(depth=(depth + 1))
        return result or None
    async def think_then_decide_and_act(self, step: NextStepModel, depth=0):
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:

            self.log_voice("I am trying to decide which action to make next.")
            decision = await self.llm().generate_function_async(
                user=self.prompt_decide_action_user(),
                system=await self.prompt_decide_action_system(),
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
            else:
                if depth >= 3: return await self.think_then_decide_and_act(step=step, depth=depth+1)
        except Exception as e:
            self.log_thought(f"An error occurred while trying to decide: {e}")
            self.log_voice("I am having trouble making a decision.")
    # HELP: Ai Tools To Help Along The Way
    async def think_then_summarize(self, content, ensure_length:int = 10000) -> str:
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
        if self.tool_plan.summary_report == "":
            report = await self.think_then_summarize(content, ensure_length)
            if report:
                self.tool_plan.summary_report = report
                return report

        content = self.ensure_within_limit(content, ensure_length)
        prompt = f"""
            {self.inject_summary_report_tag()}
            <NEW_CONTENT_TO_ADD_TO_SUMMARY>
                {content}
            </NEW_CONTENT_TO_ADD_TO_SUMMARY>
        """
        report = await self.llm().generate_async(user=prompt, system=self.prompt_summary_report_system())
        if report and str(report) != "":
            self.log_voice(f"I've updated my memory summary:\n{report}")
            self.tool_plan.summary_report = report
        return report
    # RESPOND: Review What Took Place and Generate Output
    async def think_about_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.log_voice("Umm, what should I tell the user?")
            final_response_request = self.chain_data(
                self.inject_objective_tag(),
                self.get_thoughts(),
                self.tool_plan.summary_report,
                self.inject_user_request_tag(),
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
        return self.ToolResponse(
            prefix="",
            session_id="",
            answer=final_response,
            data=self.get_data()
        )

    """ Prompts """
    def inject_tool_state_tag(self):
        return f"""
            <CURRENT_BROWSER_STATE>
                {self.tool_state.output}
            </CURRENT_BROWSER_STATE>
        """
    def inject_tool_options_tag(self):
        return f"""
            <TOOLS_AVAILABLE>
                {self.get_external_json_tools()}
            </TOOLS_AVAILABLE>
        """
    # HELP:
    def inject_summary_report_tag(self):
        return f"""
            <PROCESS_SUMMARY>
                {self.tool_plan.summary_report or 'Nothing has happen'}
            </PROCESS_SUMMARY>
        """
    def prompt_summary_report_system(self):
        return f"""
            **You keep and update an on-going summary of content you've read.**
            You are to creating an on-going summary or timeline of reading results.
            You will 'merge' the results together into 1 single memory timeline.
            {self.inject_contextual_tag()}
        """
    # ACT: Step Prompts
    async def prompt_decide_action_system(self):
        tool_state = await self.get_current_state()
        return f"""
            Review the following web html DOM index interactive elements.
            Based on the User Prompt, pick the index and tool function accordingly.
                {self.inject_voice_tag() or 'We havent said anything'}
                {self.inject_thoughts_tag() or 'We havent thought about anything.'}
                {self.inject_summary_report_tag()}
                {self.inject_decisions_tag()}
            <CURRENT_BROWSER_STATE>
                {tool_state.output}
            </CURRENT_BROWSER_STATE>
        """
    def prompt_next_step_user(self):
        return f"What do we do next to help accomplish the users request/objective to then win the game?"
    def prompt_next_step_system(self):
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
                    {self.inject_thoughts_tag()}
                    {self.inject_summary_report_tag()}
                    {self.inject_tool_options_tag()}
                    {self.inject_objective_tag()}  
                    {self.inject_plan_tag()}  
                    {self.inject_user_request_tag()}
                    {self.inject_decisions_tag()}  
                    {self.inject_tool_state_tag()}
                **REMEMBER: WE CAN NOT DO 2 THINGS AT ONCE, 1 STEP, 1 ACTION ONLY.**
            """
    # THINK:
    def prompt_objective_system(self):
        return f"""
            **Based on the users request, decide what the objective or goal is to achieve.**
            **What is the end goal?**
        """