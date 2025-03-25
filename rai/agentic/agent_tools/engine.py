
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Type

from F import LIST

from rai.agentic.aether.schema import AgentState
from rai.agentic.agent_tools.manager import ToolManager
from rai.agentic.agent_tools.module import ToolModule
from rai.agentic.agent_tools.result import ToolResult
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
            while self.checkpointQueueIsLive():

                await self.think_then_set_checkpoints()

                # while self.checkStepQueueIsLive():
                #     self.tool_plan.step_mode = "step"
                #     self.pop_next_check_step()
                #     self.log_voice(f"I am working on step {self.tool_plan.current_checkpoint_count}...")
                #     await self.think_then_decide_and_act()
                #     self.log_voice(f"I have finished step {self.tool_plan.current_checkpoint_count}...")

                self.tool_plan.step_mode = "checkpoint"
                self.pop_next_checkpoint()
                # if await self.ask_role_master_to_confirm_next_step():
                self.log_voice(f"I am working on checkpoint {self.tool_plan.current_checkpoint_count}...")
                await self.think_then_decide_and_act()
                self.log_voice(f"I have finished checkpoint {self.tool_plan.current_checkpoint_count}...")
                # if self.tool_plan.current_checkpoint_count % 2 == 0:
                self.log_voice("I am going to try and refine my checkpoint plan now.")
                await self.think_then_refine_checkpoints()


        return await self.finish_and_then_respond()
    async def setup_assistant(self, user_request: str):
        # The Assistant Process Log
        self.state = AgentState.RUNNING
        self.log_voice(f"HELLO! I am {self.tool_assistant_name()}! Let's get started!")
        self.log_voice("Hang Tight. I'm gathering your initial request the rules, documentation and data.")
        self.tool_plan.user_request = user_request
        await self.think_then_set_objective()
        await self.think_then_set_plan_type()
        await self.think_then_set_plan()
        await self.think_then_set_role_master()
        await self.think_then_set_checkpoints()
        await self.think_then_set_required_data()
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
    
    
    -> we need to keep track of accomplished checkpoints and not repeat them.
    """
    # Assistant Identity
    async def think_then_set_objective(self, depth=0):
        self.log_voice("I need to understand the users objective. What are we trying to accomplish?")
        result = await self.think.formatter_async(
            text=self.inject_user_request_tag(),
            model=Objective,
            system=self.prompt_objective_system(),
        )

        if result: self.tool_plan.overall_objective = result.objective
        elif depth <= 3: return await self.think_then_set_objective(depth=depth+1)
        self.log_voice("Okay, I think I understand the objective.")
    async def think_then_set_end_goal(self, depth=0):
        self.log_voice("I need to understand the users end goal. What is their end goal?")
        result = await self.think.generate_async(
            user=f"""
                {self.inject_objective_tag()}
                {self.inject_user_request_tag()}
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
        elif depth <= 3: return await self.think_then_set_end_goal(depth=depth+1)
        self.log_voice("Okay, I think I understand what I need to get together for the user.")
    async def think_then_set_plan_type(self, depth=0):
        self.log_voice("I need to understand the users objective. What is their end goal?")
        result = await self.think.decision_pipeline_async(
            name="agent-plans",
            request=f"""
                {self.inject_objective_tag()}
                {self.inject_user_request_tag()}
            """
        )
        if result:
            plan_type = LIST.get(0, result, "checkpoints")
            self.tool_plan.plan_type = plan_type
            self.tool_plan.plan_type_description = self.tool_plan.get_plan_type_description()
        elif depth <= 3: return await self.think_then_set_plan_type(depth=depth+1)
        self.log_voice("Okay, I have decided on the type of plan to develop.")
    async def think_then_set_plan(self):
        print("Plan Type Description", self.tool_plan.get_plan_type_description())
        result = await self.llm().generate_async(
            user=f"""
                {self.inject_user_request_tag()}
                {self.inject_objective_tag()}
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
        return result
    async def think_then_set_required_data(self, depth=0):
        self.log_voice("I need to figure out if there is required data to keep track of.")
        result = await self.think.generate_async(
            user=f"""
                {self.inject_user_request_tag()}
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
        elif depth <= 3: return await self.think_then_set_required_data(depth=depth+1)
        self.log_voice("I have created some required data I believe we will need along the way.")
    # Checkpoint Step Control
    async def think_then_set_checkpoints(self, depth=0):
        self.log_voice("I need to create a set of checkpoints.")
        if not self.checkpoint_queue_is_empty(): return
        current_ss = await self.ask_role_master_to_summarize_current_state()
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_user_request_tag()}
                {self.inject_objective_tag()}
                {self.inject_plan_tag()}
                {current_ss}
                
                Based on where we are right now, and what we are trying to do, create the checkpoints.
            """,
            model=StepCheckpoints,
            system=f"""
                {self.tool_plan.role}
                {self.inject_tool_options_tag()}
            """,
        )
        if result:
            self.tool_plan.checkpoints = result.checkpoints
            for item in result.checkpoints:
                self.add_checkpoint(NextStepModel(next_step_or_action=item.checkpoint))
        elif depth <= 3: return await self.think_then_set_checkpoints(depth=depth+1)
        self.log_voice("I have come up with a list of checkpoints to follow.")
    async def think_then_refine_checkpoints(self, depth=0):
        self.log_voice("I need to create a set of sub checkpoints steps.")
        if not self.check_step_queue_is_empty(): return
        current_ss: ToolResult = await self.get_current_state()
        result = await self.think.formatter_async(
            text=f"""
                {self.inject_all_actions_tag()}
                {self.inject_summary_report_tag()}
                {self.tool_plan.required_data}
                {current_ss.inject(current_ss)}
            """,
            model=StepCheckpoints,
            system=f"""
                You are a problem solver who uses common sense and basic logic to decide what action needs to happen next.
                **Create the next goal we need to achieve to push us forward towards the objective.**
                **You can only call one function at a time **
                ## YOUR ROLE:
                **{self.tool_plan.role}**
                {self.inject_tool_options_tag()}
            """,
        )
        if result:
            self.clear_checkpoint_queue()
            self.tool_plan.checkpoints.extend(result.checkpoints)
            for item in result.checkpoints:
                self.add_checkpoint(NextStepModel(next_step_or_action=item.checkpoint))
        # elif depth <= 3:
        #     return await self.think_then_refine_checkpoints(depth=depth + 1)
        self.log_voice("I have come up with a list of checkpoints to follow.")
    async def think_then_decide_and_act(self, depth=0):
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_tools()
            self.log_voice("I am trying to decide which action to make next.")
            decision = await self.llm().generate_function_async(
                user=await self.prompt_decide_action_user(),
                system=self.prompt_decide_action_system(),
                functions=tools,
                raw_result=True
            )

            if decision:
                if decision in self.tool_plan.decisions_made:
                    self.log_thought(f"I seem to have already done this.")
                    return await self.think_then_decide_and_act(depth=depth + 1)
                self.tool_plan.current_decision = decision[0]
                self.add_decision(decision[0])
                # if await self.ask_role_master_to_confirm_next_decision():
                action_result = await self.parse_and_call_function_async(decision)
                if action_result:
                    self.log_voice(f"I have received the action result received. Passing to Data Assistant.")
                    self.import_new_data(action_result)
                return await self.add_action_to_timeline()
            if depth >= 3: return await self.think_then_decide_and_act(depth=depth+1)
        except Exception as e:
            self.log_thought(f"An error occurred while trying to decide: {e}")
            self.log_voice("I am having trouble making a decision.")
    # Role Master
    async def think_then_set_role_master(self):
        result = await self.llm().generate_async(
            user=self.prompt_create_role_user(),
            system=self.prompt_create_role_system(),
        )
        if result: self.tool_plan.role = result
        self.log_voice("Okay, I have established a role to follow.")
        self.log_thought(f"My new role is: [ {self.tool_plan.role} ]")
        return result
    async def ask_role_master_to_summarize_current_state(self, depth=0):
        self.log_voice("Asking the role master for a summary of our current state.")
        tool_state = await self.get_current_state()
        result = self.llm().generate(
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
        self.log_voice("Asking the role master for a summary of my actions.")
        result = self.llm().generate(
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
        self.log_voice("Asking the role master for a summary of my actions.")
        tool_state = await self.ask_role_master_to_summarize_current_state()
        data_report = await self.generate_data_report()
        da_report = await self.ask_role_master_to_summarize_our_decisions_and_actions()
        result = self.llm().generate(
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
    async def ask_role_master_a_question(self, question:str, depth=0):
        self.log_voice("Asking the role master for a summary of my actions.")
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
            self.tool_plan.summary_report = result
            return result
        else:
            return "I don't know how to answer your question."
    # ACT: On-The-Fly Actions
    async def think_about_next_step(self, depth=0) -> Optional[ChainedStepModel]:
        if not self.checkpoint_queue_is_empty(): return None
        result = await self.think.formatter_async(
            text=self.prompt_next_step_user(),
            model=NextStepModel,
            system=self.prompt_next_step_system(),
        )
        if result:
            self.tool_plan.pending_checkpoint = result.next_step_or_action
            self.log_thought(f"I think the next step is [ {result.next_step_or_action} ]")
            self.log_thought(f"I am wondering if this step can be broken down further though?")
            return await self.think_then_confirm_next_step(depth=depth)
        elif depth <= 3: return await self.think_about_next_step(depth=(depth + 1))
    async def think_then_confirm_next_step(self, depth=0):
        result = await self.think.formatter_async(
            text=self.tool_plan.pending_checkpoint,
            model=IsTrueModel,
            system=f"""
                Is the User Prompt Step/Action proposed trying to call 2 or more functions?
                {self.inject_tool_options_tag()}
            """
        )
        if result:
            if not result.answer:
                self.tool_plan.current_checkpoint = self.tool_plan.pending_checkpoint
            else:
                return await self.think_then_create_next_steps(depth=(depth + 1))
        elif depth <= 3:
            return await self.think_about_next_step(depth=(depth + 1))
    async def think_then_create_next_steps(self, depth=0):
        if not self.checkpoint_queue_is_empty(): return
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
                    self.add_checkpoint(NextStepModel(next_step_or_action=item.step_action))
                self.log_thought(f"I have refined my thinking and believe the next step should be: [{self.tool_plan.current_checkpoint}]")
        elif depth <= 3:
            return await self.think_then_create_next_steps(depth=(depth + 1))

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
        self.tool_plan.current_checkpoint_count = 100

    """ PROMPTS """
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