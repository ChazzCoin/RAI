import asyncio
import datetime
import uuid
from abc import abstractmethod
from collections import deque
from contextlib import asynccontextmanager
from typing import Optional, List, Any, Union, Tuple

from F import DICT, LIST
from bs4 import BeautifulSoup

from rai.agentic.aether.schema import AgentState
from rai.agentic.agent_tools.data import ToolData
from rai.agentic.agent_tools.plan import ToolPlan
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.ai_modules import ToolLog
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel, ChainOfStepsToolFormat
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.web.soup.BodyExtractor import WebBodyExtractor


class ToolManager(ToolData, ToolLog, TextProcessor):

    @abstractmethod
    def get_tools(self) -> List[dict[str, Any]]: pass

    async def get_current_state(self) -> ToolResult:
        # explicitly specify the parent class name
        temp = await self.__class__.__name__.get_current_state(self)

        if isinstance(temp, ToolResult):
            return temp

        return ToolResult(output=str(temp))

    def log_key(self) -> str: return "tool"

    is_setup: bool = False
    state: AgentState = AgentState.IDLE
    tool_state: ToolResult = ToolResult()
    lock: asyncio.Lock = asyncio.Lock()

    name: Optional[str] = None
    tool_id: str = str(uuid.uuid4())
    tool_plan: ToolPlan = ToolPlan()
    tool_results: List['ToolResult'] = []

    soup = lambda html: BeautifulSoup(html, 'html.parser')

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
    """ Helpers """
    def checkpointQueueIsLive(self) -> bool:
        return self.maxCheckpointsHaveNotBeenMet and self.state != AgentState.FINISHED

    def checkStepQueueIsLive(self) -> bool:
        return len(self.tool_plan.check_step_queue) > 0 and self.state != AgentState.FINISHED
    async def html_to_content(self, html):
        body = await WebBodyExtractor.pipeline_async(html)
        return self.TEXT_CLEANER(body.combined_text)

    async def add_action_to_timeline(self):
        datareport = await self.generate_data_report()
        timestamp = int(datetime.datetime.utcnow().timestamp())
        action_tag = f"""
            <ACTION>
                Timestamp: {timestamp}
                Checkpoint Step: {self.tool_plan.current_checkpoint}
                Function/Decision {self.inject_latest_decision_tag()}
                Outcome: {datareport}
            </ACTION>
        """
        self.tool_plan.action_timeline[timestamp] = action_tag

    def get_latest_action(self) -> Optional[str]:
        """
        Returns the latest action (i.e. the action with the highest timestamp).
        :param action_timeline: Dictionary mapping timestamps to actions.
        :return: A tuple (timestamp, action) of the latest action, or None if empty.
        """
        if not self.tool_plan.action_timeline:
            return None
        latest_ts = max(self.tool_plan.action_timeline.keys())
        return self.tool_plan.action_timeline[latest_ts]
    def get_oldest_action(self) -> Optional[str]:
        """
        Returns the oldest action (i.e. the action with the smallest timestamp).
        :param action_timeline: Dictionary mapping timestamps to actions.
        :return: A tuple (timestamp, action) of the oldest action, or None if empty.
        """
        if not self.tool_plan.action_timeline:
            return None
        oldest_ts = min(self.tool_plan.action_timeline.keys())
        return self.tool_plan.action_timeline[oldest_ts]
    def get_actions_sorted(self) -> List[Tuple[int, str]]:
        """
        Returns all actions sorted by their timestamp in ascending order.
        :param action_timeline: Dictionary mapping timestamps to actions.
        :return: A list of tuples (timestamp, action) sorted from oldest to latest.
        """
        return sorted(self.tool_plan.action_timeline.items(), key=lambda x: x[0])
    def get_action_at(self, timestamp: int) -> Optional[str]:
        """
        Retrieves the action at a specific timestamp.
        :param action_timeline: Dictionary mapping timestamps to actions.
        :param timestamp: The specific timestamp to look up.
        :return: The action at the given timestamp, or None if not found.
        """
        return self.tool_plan.action_timeline.get(timestamp)
    def get_actions_after(self, timestamp: int) -> List[Tuple[int, str]]:
        """
        Returns all actions that occurred after a specified timestamp.
        :param action_timeline: Dictionary mapping timestamps to actions.
        :param timestamp: The timestamp to compare against.
        :return: A list of tuples (timestamp, action) for all actions with timestamps greater than the given timestamp.
        """
        return sorted(
            [(ts, act) for ts, act in self.tool_plan.action_timeline.items() if ts > timestamp],
            key=lambda x: x[0]
        )
    def get_actions_before(self, timestamp: int) -> List[Tuple[int, str]]:
        """
        Returns all actions that occurred before a specified timestamp.
        :param action_timeline: Dictionary mapping timestamps to actions.
        :param timestamp: The timestamp to compare against.
        :return: A list of tuples (timestamp, action) for all actions with timestamps less than the given timestamp.
        """
        return sorted(
            [(ts, act) for ts, act in self.tool_plan.action_timeline.items() if ts < timestamp],
            key=lambda x: x[0]
        )

    """ Tool Step Queue"""
    @property
    def maxCheckpointsHaveNotBeenMet(self) -> bool:
        return self.tool_plan.current_checkpoint_count < self.tool_plan.max_checkpoints
    @property
    def checkpoints(self) -> deque[NextStepModel]:
        return self.tool_plan.checkpoint_queue
    def add_checkpoint(self, step: NextStepModel):
        if not step: return
        if type(step) not in [NextStepModel]: return

        if not self.maxCheckpointsHaveNotBeenMet:
            self.log_thought("Max Steps have been met, the main queue is closed.")
            self.log_thought("I am adding the requested step to the overflow queue.")
            self.tool_plan.overflow_checkpoint_queue.append(step)
            return

        self.log_thought("I am adding the new step to our step queue.")
        self.tool_plan.checkpoint_queue.append(step)
    def add_checkpoints(self, steps: ChainOfStepsToolFormat):
        for chain_step in steps.chain_of_steps:
            self.add_checkpoint(NextStepModel(next_step_or_action=chain_step.step_action))
    def clear_checkpoint_queue(self):
        self.log_thought("I am clearing out the checkpoint queue.")
        self.tool_plan.checkpoint_queue.clear()
    def pop_next_checkpoint(self) -> bool:
        self.log_thought("I am grabbing the next action from our queue.")
        try:
            step = self.tool_plan.checkpoint_queue.popleft()
            if not step: return False
            self.tool_plan.previous_checkpoint = self.tool_plan.current_checkpoint
            self.tool_plan.current_checkpoint = step.next_step_or_action
            self.log_thought(f"I am about to... \n {self.tool_plan.current_checkpoint}")
            self.tool_plan.current_checkpoint_count += 1
            return True
        except Exception as e:
            self.log_thought(f"Failed to grab the next action: {e}")
            return False
    def peak_next_checkpoint(self) -> NextStepModel:
        self.log_thought("I am peaking at the next action from our queue.")
        temp = self.tool_plan.checkpoint_queue.popleft()
        self.tool_plan.checkpoint_queue.appendleft(temp)
        return temp
    def pop_oldest_checkpoint(self) -> NextStepModel:
        self.log_thought("I am grabbing the oldest action from our queue.")
        return self.tool_plan.checkpoint_queue.pop()
    def checkpoint_queue_is_empty(self) -> bool:
        return len(self.tool_plan.checkpoint_queue) == 0
    def check_step_queue_is_empty(self) -> bool:
        return len(self.tool_plan.check_step_queue) == 0
    def add_checkpoint_taken(self, step: NextStepModel):
        self.log_thought("I am adding the last action taken to the step archive.")
        self.tool_plan.checkpoints_made.append(step)
    def add_check_step(self, step: NextStepModel):
        if not step: return
        if type(step) not in [NextStepModel]: return

        # if not self.maxCheckpointsHaveNotBeenMet:
        #     self.log_thought("Max Steps have been met, the main queue is closed.")
        #     self.log_thought("I am adding the requested step to the overflow queue.")
        #     self.tool_plan.overflow_checkpoint_queue.append(step)
        #     return

        self.log_thought("I am adding the new check step to our step queue.")
        self.tool_plan.check_step_queue.append(step)
    def pop_next_check_step(self) -> bool:
        self.log_thought("I am grabbing the next check step from our step queue.")
        try:
            step = self.tool_plan.check_step_queue.popleft()
            if not step:
                self.tool_plan.current_check_step_count = 0
                return False
            self.tool_plan.previous_check_step = self.tool_plan.current_checkpoint
            self.tool_plan.current_check_step = step.next_step_or_action
            self.tool_plan.current_check_step_count += 1
            return True
        except Exception as e:
            self.log_thought(f"Failed to grab the next check step: {e}")
            return False
    """ Tool Role """
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

    """ Tool Results """
    def add_results(self, tools: List['ToolResult']):
        self.log_thought(f"I have gathered [ {len(tools)} ] results.")
        self.tool_results.extend(tools)
    def add_result(self, tool: 'ToolResult'):
        self.log_thought(f"I have gathered 1 result: {tool.output}")
        self.tool_results.append(tool)
    def add_and_pass(self, tool_or_tools: Union['ToolResult' | List['ToolResult']]) -> None | tuple[str, Any] | ToolResult | list[ToolResult]:
        if type(tool_or_tools) in [ToolResult]:
            if tool_or_tools.result_type == "tool_state":
                self.log_thought(f"I am getting a new current state update: {tool_or_tools.output}")
                self.tool_plan.current_state = tool_or_tools
            self.log_thought(f"I have gathered the results: {tool_or_tools.output}")
            self.tool_results.append(tool_or_tools)
            return tool_or_tools
        else:
            for tool in tool_or_tools:
                if tool.result_type == "tool_state":
                    self.log_thought(f"I am getting a new current state update: {tool.output}")
                    self.tool_plan.current_state = tool
                self.log_thought(f"I have gathered the results: {tool.output}")
                self.tool_results.append(tool)
            return tool_or_tools
    def count_results(self) -> int:
        items = len(self.tool_results)
        self.log_thought(f"We have gathered [ {items} ] from our actions.")
        return items
    def inject_all_results(self) -> str: return "\n".join([item.inject() for item in self.tool_results])
    def order_by_timestamp(self, descending: bool = False):
        return self.tool_results.sort(key=lambda x: x.timestamp, reverse=descending)
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

    """ Tag Injections """
    def inject_core_tags(self) -> str:
        return f"""
            {self.inject_core_user_request_tag()}
            {self.inject_core_objective_tag()}
            {self.inject_core_end_goal_tag()}
        """
    def inject_core_and_required_tags(self) -> str:
        return f"""
            {self.inject_core_tags()}
            {self.inject_required_tags()}
        """
    def inject_required_tags(self) -> str:
        return f"""
            {self.inject_required_data_tag()}
            {self.inject_required_actions_tags()}
        """
    def inject_required_actions_tags(self) -> str:
        final_results = ""
        for item in self.tool_plan.required_actions.required_actions:
            temp =f"""
                Required Action: [ {item.action} ]
                Completion Status: [ {item.iscomplete} ]
            """
            final_results += temp
        return final_results

    def inject_full_plan_tag(self) -> str:
        return f"""
            {self.tool_plan.plan_type}
            {self.tool_plan.plan_type_description}
            {self.inject_plan_tag()}
        """
    def inject_core_required_plan_tag(self) -> str:
        return f"""
            {self.inject_core_and_required_tags()}
            {self.inject_full_plan_tag()}
        """
    def inject_core_user_request_tag(self) -> str:
        return f"""
               <USER_REQUEST>
                   {self.tool_plan.user_request}
               </USER_REQUEST>
           """
    def inject_decisions_tag(self) -> str:
        decisions = ""

        for d in LIST.flatten(self.tool_plan.decisions_made):
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
    def inject_latest_decision_tag(self) -> str:
        data = DICT.get("function", self.tool_plan.current_decision, None)
        func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
        args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
        temp = f"""
            <PAST_FUNCTION_CALLS>
                Function Name: {func_name}
                Function Arguments: {args_source}
            </PAST_FUNCTION_CALLS>
        """
        return temp
    def inject_core_objective_tag(self) -> str:
        return f"""
            <OBJECTIVE>
                {self.tool_plan.overall_objective}
            </OBJECTIVE>
        """
    def inject_core_end_goal_tag(self) -> str:
        return f"""
            <END_GOAL>
                {self.tool_plan.end_goal}
            </END_GOAL>
        """
    def inject_required_data_tag(self) -> str:
        return f"""
            <REQUIRED_DATA>
                {self.tool_plan.required_data}
            </REQUIRED_DATA>
        """
    def inject_plan_tag(self) -> str:
        return f"""
            <PLAN>
                {self.tool_plan.overall_plan}
            </PLAN>
        """
    def inject_contextual_tag(self) -> str:
        return f"""
            **OBJECTIVE CONTEXT FOR SUMMARIZATION = {self.tool_plan.overall_objective}
            **PLAN CONTEXT FOR SUMMARIZATION = {self.tool_plan.overall_plan}
            **USERS REQUEST FOR CONTEXT SUMMARIZATION = {self.tool_plan.initial_request}
            **RETURN/EXTRACT A DETAILED SUMMARY OF THE RELEVANT CONTENT BASED ON CONTEXT** 
        """
    def inject_role_tag(self) -> str:
        return f"""
            <ROLE>
                {self.tool_plan.role}
            </ROLE>
        """
    def inject_next_checkpoint_tag(self) -> str:
        return f"""
            <NEXT_CHECKPOINT_TO_ACHIEVE>
                {self.tool_plan.current_checkpoint}
            </NEXT_CHECKPOINT_TO_ACHIEVE>
        """
    def inject_peak_at_future_checkpoint_tag(self) -> str:
        return f"""
            <FUTURE_CHECKPOINT_TO_ACHIEVE>
                {self.peak_next_checkpoint()}
            </FUTURE_CHECKPOINT_TO_ACHIEVE>
        """
    def inject_next_check_step_tag(self) -> str:
        return f"""
            <NEXT_STEP_TO_ACHIEVE>
                {self.tool_plan.current_check_step}
            </NEXT_STEP_TO_ACHIEVE>
        """
    def inject_latest_action_tag(self) -> str:
        return self.get_latest_action()
    def inject_all_actions_tag(self) -> str:
        all_actions = "\n".join(self.tool_plan.action_timeline.values())
        return f"{all_actions}"
    def inject_summary_report_tag(self) -> str:
        return f"""
            <PROCESS_SUMMARY>
                {self.tool_plan.summary_report}
            </PROCESS_SUMMARY>
        """
    def inject_tool_state_tag(self):
        return f"""
              <CURRENT_BROWSER_STATE>
                  {self.tool_state.inject(self.tool_state)}
              </CURRENT_BROWSER_STATE>
          """
    def inject_tool_options_tag(self):
        return f"""
              <TOOLS_AVAILABLE>
                  {self.get_tools()}
              </TOOLS_AVAILABLE>
          """
    def inject_current_checkpoint_tag(self):
        return f"""
              <CURRENT_CHECKPOINT>
                  {self.tool_plan.current_checkpoint}
              </CURRENT_CHECKPOINT>
          """
    def inject_checkpoints_tag(self):
        checkpoints = "\n".join([f"{t.order_index}. {t.checkpoint}" for t in self.tool_plan.checkpoints])
        return f"""
              <CHECKPOINTS>
                  {checkpoints}
              </CHECKPOINTS>
          """

    """ Prompt Injections """
    def prompt_create_plan_user(self):
        return f"""
        Create a detailed step by step plan for the following details.
        {self.inject_core_user_request_tag()}
        {self.inject_core_objective_tag()}
        """
    def prompt_create_plan_system(self):
        return f"""
        You are a professional step by step planner.
        **Based on the User Prompt details, create a step by step plan**
        **Each step should include one of the following functions to call with the step**
        {self.inject_tool_options_tag()}
        """
    def prompt_summary_report_system(self):
        return f"""
            **You keep and update an on-going summary of content you've read.**
            You are to creating an on-going summary or timeline of reading results.
            You will 'merge' the results together into 1 single memory timeline.
            {self.inject_contextual_tag()}
        """
    async def prompt_decide_action_user(self):
        tool_state = await self.get_current_state()
        prompt = f"""
            {self.tool_plan.required_data}
            <CURRENT_STATE>
                {tool_state.inject(tool=tool_state)}
            </CURRENT_STATE>
        """
        return prompt
    def prompt_decide_action_system(self):
        temp = self.NORMALIZER(f"""
            Review the following web html DOM index interactive elements.
            Based on the User Prompt, pick the index and tool function accordingly.
                {self.inject_tool_options_tag()}
                {self.inject_next_checkpoint_tag() if self.tool_plan.step_mode == 'checkpoint' else self.inject_next_check_step_tag()}
        """)
        # print(temp)
        return temp
    def prompt_next_step_user(self):
        return f"""
        {self.inject_decisions_tag()}  
        {self.inject_tool_state_tag()}
        Based on our current state and the decisions we have made, what should be our next single step?
        """
    def prompt_next_step_system(self):
        return self.NORMALIZER(f"""
                **Review the current state you are in.**
                **Decide the next function or action to call.**
                {self.inject_tool_options_tag()}
            """)
    def prompt_next_step_2_system(self):
        return self.NORMALIZER(f"""
            **RULES TO THE GAME**
            Pretend you are walking a 5 year old through how to accomplish the users request/objective to then win the game.
            What is the next function we need to call?
                    {self.inject_core_objective_tag()}  
                    {self.inject_decisions_tag()}  
                    {self.inject_tool_options_tag()}
            **REMEMBER: WE CAN NOT DO 2 THINGS AT ONCE, 1 STEP, 1 ACTION ONLY.**
            """)
    def prompt_objective_system(self):
        return f"""
            **Based on the users request, decide what the objective or goal is to achieve.**
            **What is the end goal?**
        """
    def prompt_role_tool_options_system(self):
        return f"""
            {self.tool_plan.role}
            {self.inject_tool_options_tag()}
        """