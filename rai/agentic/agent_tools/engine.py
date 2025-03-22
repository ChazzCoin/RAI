
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Type

from F import LIST

from rai.agentic.aether.schema import AgentState
from rai.agentic.agent_tools.manager import ToolManager
from rai.agentic.agent_tools.module import ToolModule
from rai.agentic.ai_modules.map import mMap
from rai.agentic.ai_plugins.reason import Objective, StepCheckpoints, ProposedData
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel, ChainedStepModel, ChainOfStepsToolFormat, \
    IsTrueModel

class ToolEngine(ToolModule, ToolManager, mMap, ABC):

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

    """ ASSISTANT """
    async def self_navigation(self, request: Optional[str] = None) -> str:
        await self.setup_assistant(user_request=request)
        async with self.state_context(AgentState.RUNNING):
            while self.stepQueueIsLive():
                await self.think_then_set_checkpoints()
                self.pop_next_step()
                # if await self.ask_role_master_to_confirm_next_step():
                self.log_voice(f"I am working on step {self.tool_plan.current_step_count}...")
                await self.think_then_decide_and_act()
                self.log_voice(f"I have finished step {self.tool_plan.current_step_count}...")

        return await self.finish_and_then_respond()
    async def setup_assistant(self, user_request: str):
        # The Assistant Process Log
        self.state = AgentState.RUNNING
        self.log_voice(f"HELLO! I am {self.tool_assistant_name()}! Let's get started!")
        self.log_voice("Hang Tight. I'm gathering your initial request the rules, documentation and data.")
        self.tool_plan.user_request = user_request
        await self.think_then_set_objective()
        await self.think_then_set_plan()
        await self.think_then_set_role()
        await self.think_then_set_checkpoints()
        # await self.think_then_set_required_data()
        # await self.think_then_create_next_steps()
        self.log_voice("Okay, I have the objective, plan and next step put together. Let's get started!")

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

    # ROLE

    # REFEREE

    # THINK: The Overall Assistant Identity
    async def think_then_set_objective(self, depth=0):
        self.log_voice("I need to understand the users objective. What is their end goal?")
        result = await self.think.formatter_async(
            text=self.inject_user_request_tag(),
            model=Objective,
            system=self.prompt_objective_system(),
        )

        if result: self.tool_plan.overall_objective = result.objective
        elif depth <= 3: return await self.think_then_set_objective(depth=depth+1)
        self.log_voice("Okay, I think I understand the objective.")
    async def think_then_set_plan(self):
        result = await self.llm().generate_async(
            user=f"""
                {self.inject_user_request_tag()}
                {self.inject_objective_tag()}
                {self.inject_tool_state_tag()}
                Based on our current state, what should be the following plan from here?
            """,
            system=f"""
                **Review The Following Users Request, Users Objective and Available Tools to Use.**
                **Develop a step by step plan on how to accomplish the users request/objective.**
                **Which functions should we call, in which order and with what data?**
                {self.inject_tool_options_tag()}
            """,
        )
        if result:
            self.tool_plan.overall_plan = result
        return result
    async def think_then_set_checkpoints(self, depth=0):
        self.log_voice("I need to create a set of checkpoints.")
        if not self.step_queue_is_empty(): return
        current_ss = await self.ask_role_master_to_summarize_current_state()
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_user_request_tag()}
                {self.inject_objective_tag()}
                {self.inject_plan_tag()}
                {current_ss}
            """,
            model=StepCheckpoints,
            system=f"""
                You are a concise and detailed checkpoint planner.
                **You will take the users prompt, analyze the plan and create a list of checkpoints.**
                {self.inject_tool_options_tag()}
            """,
        )
        if result:
            self.tool_plan.checkpoints = result.checkpoints
            for item in result.checkpoints:
                self.add_step(NextStepModel(next_step_or_action=item.checkpoint))
        elif depth <= 3: return await self.think_then_set_checkpoints(depth=depth+1)
        self.log_voice("I have come up with a list of checkpoints to follow.")
    async def think_then_set_role(self):
        result = await self.llm().generate_async(
            user=self.prompt_create_role_user(),
            system=self.prompt_create_role_system(),
        )
        if result: self.tool_plan.role = result
        self.log_voice("Okay, I have established a role to follow.")
        self.log_thought(f"My new role is: [ {self.tool_plan.role} ]")
        return result
    async def ask_role_master_to_confirm_next_step(self, depth=0):
        self.log_voice("Asking the role master for guidance on my next step.")
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_decisions_tag()}
                {self.inject_tool_state_tag()}
                Is the following step or action the next thing we want to do?
                {self.tool_plan.current_step}
            """,
            model=IsTrueModel,
            system=self.tool_plan.role,
        )
        if result and result.answer:
            self.log_voice(f"Role Master responded with [ {result.answer} ]")
            return result.answer
        elif depth <= 3: return await self.think_then_create_next_steps(depth=depth+1)
        self.log_voice("I have created some required data I believe we will need along the way.")
        return True
    async def ask_role_master_to_confirm_next_decision(self, depth=0):
        self.log_voice("Asking the role master for guidance on my decision.")
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_decisions_tag()}
                {self.inject_tool_state_tag()}
                {self.tool_plan.current_step}
                Is the following function call the next thing we want to do?
                {self.tool_plan.current_decision}
            """,
            model=IsTrueModel,
            system=self.tool_plan.role,
        )
        if result and result.answer:
            self.log_voice(f"Role Master responded with [ {result.answer} ]")
            return result.answer
        elif depth <= 3: return await self.think_then_decide_and_act(depth=depth+1)
        self.log_voice("I have created some required data I believe we will need along the way.")
        return True
    async def ask_role_master_to_summarize_current_state(self, depth=0):
        self.log_voice("Asking the role master for guidance on my decision.")
        tool_state = await self.get_current_state()
        result = self.llm().generate(user=f"""
            {self.inject_summary_report_tag()}
            {self.inject_decisions_tag()}
            {tool_state.inject(tool_state)}
            **Summarize our current state.**
        """, system=self.tool_plan.role)
        if result:
            self.tool_plan.current_state_summary = result
            return self.tool_plan.current_state_summary
        else:
            return "Unable to generate a summary report."
    async def think_then_set_required_data(self, depth=0):
        self.log_voice("I need to figure out if there is required data to keep track of.")
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_user_request_tag()}
                {self.inject_objective_tag()}
                {self.inject_plan_tag()}
                {self.inject_tool_options_tag()}
            """,
            model=ProposedData,
            system=f"""
                Come up with what data we need to return to the user to complete their request/objective.
            """,
        )
        if result: self.tool_plan.required_data = result.data
        elif depth <= 3: return await self.think_then_set_required_data(depth=depth+1)
        self.log_voice("I have created some required data I believe we will need along the way.")
    # ACT: On-The-Fly Actions
    async def think_about_next_step(self, depth=0) -> Optional[ChainedStepModel]:
        if not self.step_queue_is_empty(): return None
        result = await self.think.formatter_async(
            text=self.prompt_next_step_user(),
            model=NextStepModel,
            system=self.prompt_next_step_system(),
        )
        if result:
            self.tool_plan.pending_step = result.next_step_or_action
            self.log_thought(f"I think the next step is [ {result.next_step_or_action} ]")
            self.log_thought(f"I am wondering if this step can be broken down further though?")
            return await self.think_then_confirm_next_step(depth=depth)
        elif depth <= 3: return await self.think_about_next_step(depth=(depth + 1))
    async def think_then_confirm_next_step(self, depth=0):
        result = await self.think.formatter_async(
            text=self.tool_plan.pending_step,
            model=IsTrueModel,
            system=f"""
                Is the User Prompt Step/Action proposed trying to call 2 or more functions?
                {self.inject_tool_options_tag()}
            """
        )
        if result:
            if not result.answer:
                self.tool_plan.current_step = self.tool_plan.pending_step
            else:
                return await self.think_then_create_next_steps(depth=(depth + 1))
        elif depth <= 3:
            return await self.think_about_next_step(depth=(depth + 1))
    async def think_then_create_next_steps(self, depth=0):
        if not self.step_queue_is_empty(): return
        result = await self.think.formatter_async(
            text=self.prompt_next_step_user(),
            model=ChainOfStepsToolFormat,
            system=f"""
                Take the User Prompt and create the next step or action.
                Each step can only contain 1 function call.
                {self.inject_tool_options_tag()}
            """
        )
        if result:
            if type(result.chain_of_steps) in [list, tuple]:
                for item in LIST.flatten(result.chain_of_steps):
                    self.add_step(NextStepModel(next_step_or_action=item.step_action))
                self.log_thought(f"I have refined my thinking and believe the next step should be: [{self.tool_plan.current_step}]")
        elif depth <= 3:
            return await self.think_then_create_next_steps(depth=(depth + 1))
    async def think_then_decide_and_act(self, depth=0):
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:

            self.log_voice("I am trying to decide which action to make next.")
            decision = await self.llm().generate_function_async(
                user=await self.prompt_decide_action_user(),
                system=self.prompt_decide_action_system(),
                functions=self.get_tools(),
                raw_result=True
            )

            if decision:
                if decision in self.tool_plan.decisions_made:
                    self.log_thought(f"I seem to have already done this.")
                    return await self.think_then_decide_and_act(depth=depth + 1)
                self.tool_plan.current_decision = decision
                self.add_decision(decision)
                # if await self.ask_role_master_to_confirm_next_decision():
                action_result = await self.parse_and_call_function_async(decision)
                if action_result:
                    self.log_voice(f"I have received the action result received. Passing to Data Assistant.")
                    self.import_new_data(action_result)
                    return
            if depth >= 3: return await self.think_then_decide_and_act(depth=depth+1)
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
    async def think_then_understand(self, content, ensure_length:int = 10000) -> str:
        content = self.ensure_within_limit(content, ensure_length)
        return self.llm().generate(user=content, system=f"""
            Read and Analyze the User Prompt and describe what it is you are reading.
            1. Summarize the content for relevant information.
            2. Add thoughts on what you see and think about the content.
            **Be Thorough. Be Detailed**
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
            
            Summarize the overall content to keep a summarized report of what we have been doing.
        """
        report = await self.llm().generate_async(user=prompt, system=self.tool_plan.role)
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
                self.inject_thoughts_tag(),
                self.tool_plan.summary_report,
                self.inject_user_request_tag(),
                "Create a final response summary to send back to the user."
            )
            response = self.llm().generate(
                user=final_response_request,
                system=self.tool_plan.role
            )
            self.log_voice("I have come up with a response for you.")
            self.log_voice(response)
            return response
        except Exception as e:
            return self.add_problem(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")
    async def finish_and_then_respond(self) -> 'AssistResponse':
        final_response = await self.think_about_response()
        return self.ToolResponse(
            prefix="",
            session_id="",
            answer=final_response,
            data=self.get_data()
        )
    def quit(self):
        self.state = AgentState.FINISHED
        self.tool_plan.current_step_count = 100
    def prompt_create_role_user(self):
        return f"""
        Create a detailed agent role for the following details.
        {self.assistant_rules()}
        {self.map_external_class()}
        {self.inject_tool_options_tag()}
        {self.inject_user_request_tag()}
        {self.inject_objective_tag()}
        """
    def prompt_create_role_system(self):
        return f"""
        You are a professional AI Agent Role Creator.
        **Based on the User Prompt details, create a system prompt that is the 'role' the agent is playing**
        """