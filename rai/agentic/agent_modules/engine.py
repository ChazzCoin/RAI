from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from typing import Optional, Type

import asyncio
from F import LIST

from rai.agentic.aether.schema import AgentState
from rai.agentic.agent_modules.manager import ToolManager
from rai.agentic.agent_modules.module import ToolModule
from rai.agentic.agent_modules.result import ToolResult
from rai.agentic.ai_modules.map import ToolMap
from rai.agentic.ai_plugins.thoughts import ToolThoughts
from rai.agentic.pending.reason import Objective, StepCheckpoints
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel, RequiredActions

TOOL_ENGINE_REGISTRY = {}

def register_tool_engine(name: str):
    def decorator(cls):
        TOOL_ENGINE_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator

class ToolEngine(ToolManager):

    @staticmethod
    def runner(func: Callable):
        looper = asyncio.get_event_loop()
        looper.run_until_complete(func)

    @classmethod
    def registry(cls): return TOOL_ENGINE_REGISTRY

    @classmethod
    def get_tool_engine(cls, name: str) -> Type['ToolEngine']:
        return TOOL_ENGINE_REGISTRY.get(name)[0]

    @staticmethod
    def module_name() -> str: return 'tool-engine'
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

    """ BETA-ASSISTANT """
    def generate_mini_plan(self, request: str):
        """AI CALL: Generate a chain-of-steps plan based on the provided prompt."""
        try:
            steps = self.llm().tool("chain-of-steps", request)
            plan = [f"<ACTION> {step.order_index}. {step.step_action} </ACTION>" for step in steps]
            self.log_voice("\nGenerated the following Action Plan\n", "\n".join(plan))
            return steps
        except Exception as e:
            self.log_voice(f"Failed to generate a plan. [ {str(e)} ]")
            return [request]
    async def call(self, request: str):
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_tools()
            self.log_voice("Based on what I want to do next, I need to decide which function to call.")
            decision = await self.llm().generate_function_async(
                user=request,
                system=self.assistant_rules(),
                functions=tools,
                raw_result=True
            )
            if decision: return await self.parse_and_call_function_async(decision)
            return None
        except Exception as e:
            self.log_thought(f"An error occurred while trying to decide: {e}")
            self.log_voice("I am having trouble making a decision.")
            return None
    @classmethod
    async def ask(cls, request: str) -> 'ToolResponse':
        self = cls()
        await self.setup_assistant(request)
        try:
            max_steps = 10
            step_queue = deque(self.generate_mini_plan(request=request) or [])
            steps_taken = 0

            # Process the queue until it's empty or the objective is met.
            while step_queue:
                step = step_queue.popleft()
                steps_taken += 1
                try:
                    action = self.tag_data("ACTION", f"{steps_taken}.{step.step_action}")
                    result = await self.call(request=action)
                    self.import_result_and_pass(result)
                except Exception as e:
                    self.log_voice(f"Failed to complete step [{steps_taken}]", str(e))

                if max_steps < steps_taken: break

            self.log_voice("")
            data = self.get_data()
            return self.ToolResponse(
                prefix=self.tool_plan.prefix,
                session_id=self.tool_plan.session_id,
                answer="I have completed your request.",
                data=data
            )
        except Exception as e:
            self.log_voice(f"Overall Reasoning Error: [ {str(e)} ]")
            return self.ToolResponse(
                prefix=self.tool_plan.prefix,
                session_id=self.tool_plan.session_id,
                answer=f"I have failed to complete your request. [ {str(e)} ]",
                data=None
            )
    """ AGENT """
    @classmethod
    async def go(cls, request: Optional[str] = None) -> 'ToolResponse':
        return await cls().self_navigation(request=request)
    async def self_navigation(self, request: Optional[str] = None) -> 'ToolResponse':
        # self.r_switch_engine('ollama')
        await self.setup_assistant(user_request=request)
        await self.setup_navigation()
        async with self.state_context(AgentState.RUNNING):
            while self.checkpointQueueIsLive():
                await self.decide_the_next_action()
                self.tool_plan.step_mode = "checkpoint"
                self.pop_next_checkpoint()
                self.log_voice(f"I am working on the next action: {self.tool_plan.current_checkpoint_count}...")
                await self.decide_the_function_to_call()
                if self.final_response: break
                self.log_voice(f"I have finished the action: {self.tool_plan.current_checkpoint_count}...")
                self.log_voice("I am going to try and refine my checkpoint plan now.")
                await self.decide_a_refined_action()
        return await self.finish_and_then_respond()
    async def setup_assistant(self, user_request: str):
        # The Assistant Process Log
        self.state = AgentState.RUNNING
        self.log_voice(f"HELLO! I am {self.tool_assistant_name()}! Let's get started!")
        self.log_voice("Hang Tight. I'm gathering all the requirements and setting myself up.")
        self.tool_plan.user_request = user_request
        await self.think_then_set_core_objective()
        await self.think_then_set_core_end_goal()
        await self.think_then_set_core_required_data()
        await self.think_then_set_core_required_actions()
        self.log_voice("All setup. It is time to accomplish a task!")
    async def setup_navigation(self):
        await self.think_then_set_plan_type()
        await self.think_then_set_plan()
        await self.think_then_set_role_master()
        await self.decide_the_next_action()
        self.log_voice("I have thought about ")
    """ Thinking """
    # CORE
    async def think_then_set_core_objective(self, depth=0):
        self.log_voice("I need to understand the users objective. What are we trying to accomplish?")
        result = await self.think.formatter_async(
            text=self.inject_core_user_request_tag(),
            model=Objective,
            system=self.prompt_objective_system(),
        )

        if result: self.tool_plan.overall_objective = result.objective
        elif depth <= 3: return await self.think_then_set_core_objective(depth=depth + 1)
        self.log_voice("Okay, I think I understand the objective.")
    async def think_then_set_core_end_goal(self, depth=0):
        self.log_voice("I need to understand the users end goal.")
        result = await self.think.generate_async(
            user=f"""
                {self.inject_core_objective_tag()}
                {self.inject_core_user_request_tag()}
                What is the end goal we are trying to achieve? What information or data do we need to put together to return back?
            """,
            system=f"""
                You are a master at understanding a users request and what is needed to be put together to return back.
                Based on the users request, the objective and tools at hand, what is the user asking to have returned to them?
                What information or data is needed to be put together and returned back to the user?
                {self.inject_tool_options_tag()}
                {self.assistant_rules()}
            """,
        )
        if result: self.tool_plan.end_goal = result
        elif depth <= 3: return await self.think_then_set_core_end_goal(depth=depth + 1)
        self.log_voice("Okay, I think I understand what I need to get together for the user.")
    async def think_then_set_core_required_data(self, depth=0):
        self.log_voice("I need to figure out if there is required data to keep track of.")
        result = await self.think.generate_async(
            user=f"""
                {self.inject_core_user_request_tag()}
            """,
            system=f"""
                Extract the relevant data from the User Prompt that we need to remember throughout the task.
                ## Example Data to Extract for Memory
                1. Usernames/Passwords
                2. Names, Places, People, Locations.
                3. Information that we may need later to finish the objective
            """,
        )
        if result: self.tool_plan.required_data = result
        elif depth <= 3: return await self.think_then_set_core_required_data(depth=depth + 1)
        self.log_voice("I have created some required data I believe we will need along the way.")
    async def think_then_set_core_required_actions(self, depth=0):
        self.log_voice("I need to figure out if there is required actions to keep track of.")
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_core_user_request_tag()}
                {self.inject_required_data_tag()}
            """,
            model=RequiredActions,
            system=f"""
                Extract the relevant actions from the User Prompt/Plan that we need to remember throughout the task.
                ## Example Data to Extract for Memory
                1. Logging into something
                2. Finding something
                3. Verifying something
                4. Do Something
                5. DONT do something
            """,
        )
        if result: self.tool_plan.required_actions = result
        elif depth <= 3: return await self.think_then_set_core_required_actions(depth=depth + 1)
        self.log_voice("I have created some required actions I believe we will need along the way.")
    # PLAN
    async def think_then_set_plan_type(self, depth=0):
        self.log_voice("I am coming up with a plan type to develop.")
        result = await self.think.decision_pipeline_async(
            name="agent-plans",
            request=self.inject_core_tags()
        )
        if result:
            plan_type = LIST.get(0, result, "checkpoints")
            self.tool_plan.plan_type = plan_type
            self.tool_plan.plan_type_description = self.tool_plan.get_plan_type_description()
        elif depth <= 3: return await self.think_then_set_plan_type(depth=depth+1)
        self.log_voice("Okay, I have decided on the type of plan to develop.")
    async def think_then_set_plan(self):
        self.log_voice("I am going to put together an official plan to follow now.")
        result = await self.llm().generate_async(
            user=f"""
                {self.inject_core_tags()}
                {self.tool_plan.plan_type}
                {self.tool_plan.plan_type_description}
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
        self.log_voice("Alrighty, got the plan put together.")
        return result
    # DECIDE AND ACT
    async def decide_the_next_action(self, depth=0):
        self.log_voice("I need to now figure out what we need to start doing...")
        if not self.checkpoint_queue_is_empty(): return
        current_ss = await self.ask_role_master_to_summarize_current_state()
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_core_required_plan_tag()}
                {current_ss}
                **Based on where we are right now, and what we are trying to do, create the checkpoints.**
            """,
            model=StepCheckpoints,
            system=self.prompt_role_tool_options_system(),
        )
        if result:
            self.tool_plan.checkpoints = result.checkpoints
            for item in result.checkpoints:
                self.add_checkpoint(NextStepModel(next_step_or_action=item.checkpoint))
        elif depth <= 3: return await self.decide_the_next_action(depth=depth + 1)
        self.log_voice("I have come up with a list of initial actions to make.")
    async def decide_a_refined_action(self, depth=0):
        self.log_voice("Let me take a look at where we are, see how I need to adjust my next action.")
        current_ss: ToolResult = await self.get_current_state()
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_all_actions_tag()}
                {self.inject_summary_report_tag()}
                {self.inject_core_required_plan_tag()}
                {current_ss.inject(current_ss)}
            """,
            model=StepCheckpoints,
            system=f"""
                You are a problem solver who uses common sense and basic logic to decide what action needs to happen next.
                **Create the next goal we need to achieve to push us forward towards the objective.**
                **You can only call one function at a time **
                ## YOUR ROLE:
                {self.prompt_role_tool_options_system()}
            """,
        )
        if result:
            self.log_voice("Alright, I know what I want to do next.")
            self.clear_checkpoint_queue()
            self.tool_plan.checkpoints.extend(result.checkpoints)
            for item in result.checkpoints:
                self.add_checkpoint(NextStepModel(next_step_or_action=item.checkpoint))
    async def decide_the_function_to_call(self, depth=0):
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_tools()
            self.log_voice("Based on what I want to do next, I need to decide which function to call.")
            decision = await self.llm().generate_function_async(
                user=await self.prompt_decide_action_user(),
                system=self.prompt_decide_action_system(),
                functions=tools,
                raw_result=True
            )
            if decision: return await self.handle_decision(decision)
            elif depth <= 3: return await self.decide_the_function_to_call(depth=depth + 1)
        except Exception as e:
            self.log_thought(f"An error occurred while trying to decide: {e}")
            self.log_voice("I am having trouble making a decision.")
    async def handle_decision(self, decision):
        self.log_voice("I have decided on the function.")
        if decision in self.tool_plan.decisions_made:
            self.log_thought(f"I seem to have already done this.")
            return await self.decide_the_function_to_call()
        self.tool_plan.current_decision = decision[0]
        self.add_decision(decision[0])
        # if await self.ask_role_master_to_confirm_next_decision():
        self.log_voice("I am going to call the function now.")
        action_result = await self.parse_and_call_function_async(decision)
        if self.final_response: return self.final_response
        if action_result:
            self.log_voice(f"The function seems to have returned something, I am going to take a deeper look at the data given to me.")
            self.import_result_and_pass(action_result)
            if self._holding_data and self._is_store_documents:
                self.quit()
                return await self.finish_and_then_respond()
        else:
            self.log_voice(f"The function was called but either no data came back or something went wrong. I am looking into it.")
        return await self.add_action_to_timeline()
    # ASK ROLE MASTER
    async def think_then_set_role_master(self):
        self.log_voice("I am putting together a role master to help me along the way.")
        result = await self.llm().generate_async(
            user=self.prompt_create_role_user(),
            system=self.prompt_create_role_system(),
        )
        if result: self.tool_plan.role = result
        self.log_voice("Okay, I have established a role master to follow.")
        self.log_thought(f"My new role is: [ {self.tool_plan.role} ]")
        return result
    async def ask_role_master_a_question(self, question:str, depth=0):
        self.log_voice(f"Asking the role master a question real quick... [ {question} ]")
        # tool_state = await self.ask_role_master_to_summarize_current_state()
        state:ToolResult = await self.get_current_state()
        da_report = await self.ask_role_master_to_summarize_our_decisions_and_actions()
        result = await self.llm().generate_async(
            user=f"""
                {da_report}
                {self.inject_decisions_tag()}
                {state.inject(state)}
                QUESTION: {question}
            """,
            system=f"""
                {self.tool_plan.role}
                Review the data provided and answer the user prompts question.
            """
        )
        if result:
            self.log_voice(f"The Role Master has responded...\n {result} ")
            self.tool_plan.summary_report = result
            return result
        else:
            return "I don't know how to answer your question."
    async def ask_role_master_to_understand(self, content, ensure_length:int = 10000) -> str:
        self.log_voice("I am analyzing some content to better understand what it is.")
        content = self.ensure_within_limit(content, ensure_length)
        return await self.llm().generate_async(user=content, system=f"""
            Read and Analyze the User Prompt and describe what it is you are reading.
            1. Summarize the content for relevant information.
            2. Add thoughts on what you see and think about the content.
            **Be Thorough. Be Detailed**
            {self.inject_role_tag()}
        """)
    async def ask_role_master_to_summarize(self, content, ensure_length:int = 10000) -> str:
        self.log_voice("I am summarizing some content real quick.")
        content = self.ensure_within_limit(content, ensure_length)
        result = await self.llm().generate_async(
            user=f"""
                **Summarize the following content, make sense of it.**
                **I want to know, Who, What, When, Where, How, Why!?**
                {content}
            """,
            system=self.tool_plan.role
        )
        return result
    async def ask_role_master_to_summarize_current_state(self, depth=0):
        self.log_voice("Asking the role master for a summary of our current state.")
        tool_state = await self.get_current_state()
        result = await self.llm().generate_async(
            user=f"""
                {self.inject_summary_report_tag()}
                {self.inject_latest_action_tag()}
                {tool_state.inject(tool_state)}
                **Summarize our current state.**
                **Where are we, what are we doing? I want to know, Who, What, When, Where, Why!?**
            """,
            system=self.tool_plan.role
        )
        if result:
            self.tool_plan.current_state_summary = result
            return self.tool_plan.current_state_summary
        else:
            self.log_thought("Unable to generate a current state summary report.")
            return tool_state.inject(tool_state)
    async def ask_role_master_to_summarize_our_decisions_and_actions(self, depth=0):
        self.log_voice("Asking the role master for a summary of my decisions and actions.")
        result = await self.llm().generate_async(
            user=f"""
                {self.inject_all_actions_tag()}

                **Summarize what we have done so far.**
                **What our decisions have been, the actions made from them and what results we got from it.**
                **A cause and effect breakdown**
            """,
            system=self.tool_plan.role
        )
        if result:
            self.tool_plan.decisions_and_actions_summary = result
            return self.tool_plan.decisions_and_actions_summary
        else:
            self.log_thought("Unable to generate a summary of my decisions and actions.")
    async def ask_role_master_to_summarize_what_we_have_done(self, depth=0):
        self.log_voice("Asking the role master for a summary of what I have been doing.")
        tool_state = await self.ask_role_master_to_summarize_current_state()
        data_report = await self.generate_data_report()
        da_report = await self.ask_role_master_to_summarize_our_decisions_and_actions()
        result = await self.llm().generate_async(
            user=f"""
                {data_report}
                {da_report}
                {tool_state}
                **Summarize what we have done so far. A step by step timeline.**
            """,
            system=self.tool_plan.role
        )
        if result:
            self.tool_plan.action_timeline_summary = result
            return self.tool_plan.action_timeline_summary
        else:
            self.log_thought("Unable to generate a summary of my actions.")
    async def ask_role_master_for_a_summary_report(self, content, ensure_length:int = 10000) -> str:
        self.log_voice("I am condensing my research to help me remember it better.")
        if self.tool_plan.summary_report == "":
            report = await self.ask_role_master_to_summarize(content, ensure_length)
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
    # FINISH AND RESPOND: Review What Took Place and Generate Output
    async def think_about_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.log_voice("Umm, it is time to finish up, what should I tell the user?")
            final_response_request = self.chain_data(
                self.inject_core_objective_tag(),
                self.inject_thoughts_tag(),
                self.tool_plan.summary_report,
                self.inject_core_user_request_tag(),
                "Create a final response summary to send back to the user."
            )
            response = self.llm().generate(
                user=final_response_request,
                system=self.tool_plan.role
            )
            self.log_voice("I have come up with a response for you...")
            self.log_voice(response)
            return response
        except Exception as e:
            return self.add_problem(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")
    async def finish_and_then_respond(self) -> 'ToolResponse':
        if self.final_response: return self.final_response
        self.quit()
        f_response = await self.think_about_response()
        data = self.get_data()
        self.final_response = self.ToolResponse(
            prefix=self.tool_plan.prefix,
            session_id=self.tool_plan.session_id,
            answer=f_response,
            data=data
        )
        return self.final_response
    def quit(self):
        self.state = AgentState.FINISHED
        self.tool_plan.current_checkpoint_count = 100
    def attach_data_and_send_result(self, results) -> ToolResult:
        return ToolResult(
            output="We have attached data to the holder.",
            success=True,
            holding=self._required_data_model_type().__class__.__name__,
            holder=results
        )
    """ PROMPTS """
    def prompt_create_role_user(self):
        return f"""
        Create a detailed agent role for the following details.
        {self.inject_core_tags()}
        {self.inject_full_plan_tag()}
        """
    def prompt_create_role_system(self):
        return f"""
        You are a professional AI Agent Role Creator.
        **Based on the User Prompt details, create a system prompt that is the 'role' the agent is playing**
        {self.assistant_rules()}
        {self.map_external_class()}
        {self.inject_tool_options_tag()}
        """