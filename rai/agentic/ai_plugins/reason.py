import asyncio
import inspect
from abc import ABC, abstractmethod
from collections import deque
from contextlib import asynccontextmanager
from typing import Any, List, Type, Optional, Union

from pydantic import BaseModel
from pydantic.v1 import Field

from rai.agentic.aether.schema import AgentState
from rai.agentic.aether.tool import ToolResult, ToolResults
from rai.agentic.ai_modules import mAssistLog
from rai.agentic.ai_modules.data import mData
from rai.agentic.ai_modules.map import mMap
from rai.agentic.ai_modules.r import rModule
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.agentic.ai_tools.text_tools.text_formats import StepModel, NextStepModel
from rai.ingest.utilities.TextUtils import TextProcessor

# ASSISTANT_LOG_CHAIN is assumed to be defined globally
ASSISTANT_LOG_CHAIN = []


class HtmlInputElement(BaseModel):
    type: Optional[str] = Field(None, description="Type of the input field")
    name: Optional[str] = Field(None, description="Name attribute of the input field")
    id: Optional[str] = Field(None, description="ID attribute of the input field")
    placeholder: Optional[str] = Field(None, description="Placeholder attribute of the input field")
    value: Optional[str] = Field(None, description="Value attribute of the input field")
    label: Optional[str] = Field(None, description="Associated label text for the input field")


class HtmlButtonElement(BaseModel):
    type: Optional[str] = Field(None, description="Type of the button")
    name: Optional[str] = Field(None, description="Name attribute of the button")
    id: Optional[str] = Field(None, description="ID attribute of the button")
    text: Optional[str] = Field(None, description="Text inside the button")


class HtmlWebElements(BaseModel):
    inputs: List[HtmlInputElement] = []
    buttons: List[HtmlButtonElement] = []

class HtmlDecisionElement(BaseModel):
    element: Union[HtmlButtonElement | HtmlInputElement]

class Objective(BaseModel):
    objective: str = Field("", description="The objective to accomplish or achieve.")

class Objectives(BaseModel):
    objectives: List[Objective] = []
class ReconUrl(BaseModel):
    url: str = Field("", description="Url to navigate and gather information about.")

class ReconUrls(BaseModel):
    urls: List[ReconUrl] = []

class SearchTerms(BaseModel):
    search_terms: List[str]

class DOMIndex(BaseModel):
    index: int

class rAssistantReasoningPlugin(rModule, mMap, mData, mAssistLog, ABC):
    """
    A reasoning assistant plugin that coordinates the process of generating plans,
    selecting functions to call, and ultimately driving the agent's behavior.
    Extend this abstract class to create specialized assistants.
    """
    is_setup: bool = False
    overall_objective = "Unknown Objective"
    objectives: Objectives = Objectives()

    tool_results = ToolResults()

    overall_plan = "Unknown Plan"

    steps_taken: List[NextStepModel] = []
    previous_step: Optional[NextStepModel] = None
    current_step: Optional[NextStepModel] = None
    required_data: Optional[Any] = None

    tool_result_log: List[str] = ["Which website should we navigate to first?"]

    def tool_result_log_str(self) -> str:
        return "\n".join(self.tool_result_log)

    state: AgentState = AgentState.IDLE
    max_steps = 10
    current_step_count = 0
    objective_is_complete = False

    assistant_system_prompt = ""
    user_request_prompt = ""

    ext_documentation_tagged = "<ExternalDocumentation> </ExternalDocumentation>"
    int_documentation_tagged = "<InternalDocumentation> </InternalDocumentation>"
    assistant_rules_tagged = f"<RULES> </RULES>"
    attached_data_tagged = f"<ATTACHED DATA> </ATTACHED DATA>"
    initial_request_tagged = f"<USER REQUEST> </USER REQUEST>"

    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def assistant_rules() -> str:
        """Return the assistant rules as a string."""
        pass

    @staticmethod
    @abstractmethod
    def _required_model() -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        pass

    """ EXTERNAL PROMPTS """
    def external_decision_prompt(self) -> str:
        """Construct and return the prompt used to decide the best function/tool to select."""
        return f"""
            **Based on the following setup and the User Prompt below, determine the best Function/Tool to select and call.**
            <External Class Documentation>
                {self.map_external_class()}
            </External Class Documentation>
            <External Assistant Rules>
                {self.assistant_rules()}
            </External Assistant Rules>
            <OBJECTIVE>
                {self.overall_objective}
            </OBJECTIVE>
                {self.initial_request_tagged}
            <ASSISTANT LOG>
                {self.get_assistant_log_str()}
            </ASSISTANT LOG>
            <PLAN>
                {self.overall_plan}
            </PLAN>
            <STEP>
                {self.current_step.next_step_or_action}
            </STEP>
        """
    def navigation_decision_prompt(self) -> str:
        """Construct and return the prompt used to decide the best function/tool to select."""
        return f"""
            **You are a web based recon/information gatherer, determine the next webpage/url to navigate to.**
            
            <OBJECTIVE>
                {self.overall_objective}
            </OBJECTIVE>
                {self.initial_request_tagged}
            <ASSISTANT LOG>
                {self.get_assistant_log_str()}
            </ASSISTANT LOG>
            <PLAN>
                {self.overall_plan}
            </PLAN>
        """
    def external_plan_prompt(self) -> str:
        return self.chain_data(
            self.ext_documentation_tagged,
            self.assistant_rules_tagged,
            self.attached_data_tagged,
            self.get_log_str("DATA"),
            self.initial_request_tagged
        )

    """ REASONING ENGINE FUNCTIONALITY """
    def get_tool(self, function_name:str) -> dict[str, Any]:
        """
        Inspect the class for public callable methods and return a list of dictionaries,
        each formatted in a robust JSON Schema style for external calls.
        """
        func_obj = {}
        # Iterate over only the methods defined in this class (parent) itself.
        for name, member in self.__class__.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(member, (staticmethod, classmethod)):
                if name.startswith(function_name):
                    func_obj = member.__func__
                    break
            elif inspect.isfunction(member):
                if name.startswith(function_name):
                    func_obj = member
                    break
        return self.function_to_schema(func_obj)
    async def ask_ai_to_decide_which_search_next(self) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tool = self.get_tool(function_name="search")
            tool['function']['description'] = "Takes in basic str natural language input to search with google.com"
            self.assistant_log("Attempting to search google...")
            decision = await self.llm().generate_function_async(
                user=self.tool_result_log_str(),
                system=self.navigation_decision_prompt(),
                functions=[tool],
                raw_result=True
            )
            self.assistant_log(f"Navigation decision made: [ {decision} ]")
            return decision
        except Exception as e:
            return self.assistant_error_log("Error in deciding function:", str(e))
    def ask_ai_to_decide_which_function_to_call(self, user_prompt: str) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_external_json_tools()
            self.assistant_log("Attempting to decide on a function.")
            decision = self.llm().generate_function(
                user=user_prompt,
                system=self.external_decision_prompt(),
                functions=tools,
                raw_result=True
            )
            self.assistant_log(f"Decision made: [ {decision} ]")
            return decision
        except Exception as e:
            return self.assistant_error_log("Error in deciding function:", str(e))

    def ask_ai_if_objective_is_completed(self) -> bool:
        """AI CALL: Check whether the objective has been completed based on the given prompt."""
        try:
            self.assistant_log("Checking if objective has been completed.")
            has_data = f"FLAG FOR IF WE HAVE DATA READY FOR THE USER: [ {self.has_data()} ]"
            response = rTextTools.tool(
                name="is_true",
                user_prompt=self.chain_data(
                    self.get_assistant_log_str(),
                    self.get_log_str("DATA")
                ),
                system_prompt=f"""
                    Based on the data provided, have we completed the objective?
                    <OBJECTIVE>
                        {self.overall_objective}
                    </OBJECTIVE>
                    
                    <PLAN>
                        {self.overall_plan}
                    </PLAN>
                    
                        {self.initial_request_tagged}
                """,
            )
            self.assistant_log(f"Objective completion check: {response}")
            return response
        except Exception as e:
            self.assistant_error_log("Failed to verify if the objective has been completed.", str(e))
            return False
    def ask_ai_if_action_needs_retry(self) -> bool:
        """AI CALL: Check whether the objective has been completed based on the given prompt."""
        try:
            self.assistant_log("Checking if retrying last action is necessary.")

            prompt = f"""
                <STEPS_TAKEN>
                    {self.get_steps_taken_str()}
                </STEPS_TAKEN>
                <LAST_STEP_TAKEN>
                    {self.current_step.step}
                </LAST_STEP_TAKEN>
                <LAST_STEP_TAKEN_RESULT>
                    {self.current_step.result}
                </LAST_STEP_TAKEN_RESULT>
            """

            response = rTextTools.tool(
                name="is_true",
                user_prompt=prompt,
                system_prompt=f"""
                    Based on the assistant process log provided, do we retry the previous function call/action?
                    <ASSISTANT_LOG>
                        {self.get_assistant_log_str()}
                    </ASSISTANT_LOG>
                """,
            )
            self.assistant_log(f"Action Retry Check Response: {response}")
            return response
        except Exception as e:
            self.assistant_error_log("Failed to check if action should be retried.", str(e))
            return False
    def ask_ai_to_generate_a_request_plan(self) -> List[Any]:
        """AI CALL: Generate a chain-of-steps plan based on the provided prompt."""
        try:
            steps = rTextTools.tool("chain-of-steps", TextProcessor.NORMALIZER(self.external_plan_prompt()))
            plan = [f"<ACTION> {step.order_index}. {step.step_action} </ACTION>" for step in steps]
            self.assistant_log("\nGenerated the following Action Plan\n", "\n".join(plan))
            return steps
        except Exception as e:
            self.assistant_error_log("Failed to generate a plan.", str(e))
            return []
    def ask_ai_to_establish_objective(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Attempting to establish objective.")
            objective_request = self.chain_data(
                self.map_external_class(),
                self.assistant_rules_tagged,
                self.initial_request_tagged
            )
            response = rTextTools.tool(
                "objective-summary",
                user_prompt=objective_request
            )
            self.assistant_log(f"Established objective: {response}")
            return response
        except Exception as e:
            return rAssistantReasoningPlugin.assistant_error_log("Failed to establish an objective.", str(e))
    def ask_ai_to_generate_final_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Generating final response for user.")
            final_response_request = self.chain_data(
                self.assistant_rules_tagged,
                self.attached_data_tagged,
                self.get_assistant_log_str(),
                self.log_data("DATA"),
                self.initial_request_tagged,
            )
            response = self.llm().generate(
                user=final_response_request,
                system="Based on the data provided, create the appropriate response to send back to the user."
            )
            self.assistant_log("Final Response Generated", response)
            return f"<FINAL RESPONSE>\n{response}\n</FINAL RESPONSE>"
        except Exception as e:
            return self.assistant_error_log(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")

    """ Assistant Core Functions"""
    async def setup_assistant(self, user_request:str, **attached_data):
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
        # Establish the objective.
        self.overall_objective = await self.get_set_objective_async()
        self.overall_plan = await self.get_set_plan_async()
        self.is_setup = True

    def make_call(self, previous_decision=None, depth=0):
        if depth >= 10: return None
        result = previous_decision
        if not previous_decision:
            try:
                prompt = f"""
                     {self.map_external_class()}
                     {self.overall_objective}
                     {self.initial_request_tagged}
                 """
                result = self.ask_ai_to_decide_which_function_to_call(prompt)
                self.assistant_log(f"Decision Result: {result}")
            except Exception as e:
                self.assistant_log(f"Decision Failure: {str(e)}")
                return self.make_call(previous_decision, depth + 1)
        try:
            call_result = self.parse_and_call_function(result)
            self.assistant_log(f"Function Call Result: {call_result}")
            return self.import_new_data(call_result)
        except Exception as e:
            self.assistant_log(f"Function Call Failed: {str(e)}")
            return self.make_call(previous_decision, depth + 1)
    def make_action(self, action, previous_decision=None, depth=0):
        if depth >= 10: return None
        result = previous_decision
        self.assistant_log(f"Attempting to Make Action: {action} \n Retry Depth [ {depth} ]")
        if not previous_decision:
            try:
                result = self.ask_ai_to_decide_which_function_to_call(action)
                self.assistant_log(f"Decision Result: {result}")
            except Exception as e:
                self.assistant_log(f"ERROR: Decision Failure, attempting retry [ {depth} ]: {str(e)}")
                return self.make_action(action, previous_decision, depth + 1)
        try:
            call_result = self.parse_and_call_function(result)
            self.assistant_log(f"Function Call Result: {call_result}")
            return self.import_new_data(call_result)
        except Exception as e:
            self.assistant_log(f"ERROR: Function Call Failed, attempting retry [ {depth} ]: {str(e)}")
            return self.make_action(action, previous_decision, depth + 1)

    async def make_action_async(self, action, previous_decision=None, depth=0):
        if depth >= 10: return None
        result = previous_decision
        self.assistant_log(f"Attempting to Make Action: {action} \n Retry Depth [ {depth} ]")
        if not previous_decision:
            try:
                result = self.ask_ai_to_decide_which_function_to_call(action)
                self.assistant_log(f"Decision Result: {result}")
            except Exception as e:
                self.assistant_log(f"ERROR: Decision Failure, attempting retry [ {depth} ]: {str(e)}")
                return await self.make_action_async(action, previous_decision, depth + 1)
        try:
            call_result = await self.parse_and_call_function_async(result)
            self.assistant_log(f"Function Call Result: {call_result}")
            return self.import_new_data(call_result)
        except Exception as e:
            self.assistant_log(f"ERROR: Function Call Failed, attempting retry [ {depth} ]: {str(e)}")
            return await self.make_action_async(action, previous_decision, depth + 1)

    def respond(self) -> 'AssistResponse':
        final_response = self.ask_ai_to_generate_final_response()
        return self.AssistResponse(
            prefix="",
            session_id="",
            answer=final_response,
            data=self.get_data()
        )

    """ Single Hit Approach """
    def request(self, user_request: str, **attached_data) -> 'AssistResponse':
        self.setup_assistant(user_request, **attached_data)
        self.make_call()
        return self.respond()


    def ask_if_objective_is_completed(self) -> bool:
        """AI CALL: Check whether the objective has been completed based on the given prompt."""
        try:
            self.assistant_log("Checking if objective has been completed.")

            response = self.llm().tool(
                name="is_true",
                user_prompt=self.decide_objective_completion_prompt(),
                system_prompt="Based on the data provided, have we completed the objective?",
            )
            self.assistant_log(f"Objective completion check: {response}")
            if response is not None: self.objective_is_complete = response
            return response
        except Exception as e:
            self.assistant_error_log("Failed to verify if the objective has been completed.", str(e))
            return False

    """ Reasoning Multi-Step Planned Approach """
    def reason(self, user_request: str, **attached_data) -> 'AssistResponse':
        """
        1. Objective
        2. Plan/Steps
        3. Did we accomplish the objective?
            4. YES: -> Generate final response, break queue and finish.
            5. NO:  -> Create Next-Step Plan and add to queue, then run queue.
            6. Did we accomplish the objective?

        Main reasoning method that:
          1. Gathers and formats context, rules, and attached data.
          2. Establishes the objective.
          3. Generates and processes a step-by-step plan using a step/action queue.
          4. Checks for objective completion.

          self.int_documentation_tagged = self.map_internal_class()
        """
        try:
            self.setup_assistant(user_request, **attached_data)

            # Initialize the step/action queue.
            max_steps = 10
            step_queue = deque(self.ask_ai_to_generate_a_request_plan() or [])
            steps_taken = 0

            # Process the queue until it's empty or the objective is met.
            while step_queue:
                step = step_queue.popleft()
                steps_taken += 1
                try:
                    action = self.tag_data("ACTION", f"{steps_taken}.{step.step_action}")
                    self.make_action(action=action)
                    # Check if the objective is accomplished.
                    if self.ask_ai_if_objective_is_completed():
                        self.assistant_log(f"Objective completed on step [{steps_taken}]")
                        break
                    if self.ask_ai_if_action_needs_retry():
                        self.assistant_log(f"Determined action should be retried on step [{steps_taken}]")
                        self.make_action(action=action)
                        if self.ask_ai_if_objective_is_completed():
                            self.assistant_log(f"Objective completed on step [{steps_taken}]")
                            break
                    # handle error/no decision...
                except Exception as e:
                        self.assistant_error_log(f"Failed to complete step [{steps_taken}]", str(e))

                if max_steps < steps_taken: break

            # Final check for objective completion after processing the queue.
            self.assistant_log("Final objective completion check after empty queue.")
            return self.respond()
        except Exception as e:
            self.assistant_error_log(f"Overall Reasoning Error: [ {str(e)} ]")
            return self.respond()

    async def recon_mode(self):

        recon_steps = 10
        recon_step_count = 0

        async def navigate_to_next_page_async(previous_decision=None, depth=0):
            if depth >= 10: return None
            result = previous_decision
            self.assistant_log(f"Attempting to Recon Next Page. \n Retry Depth [ {depth} ]")
            if not previous_decision:
                try:
                    result = await self.ask_ai_to_decide_which_search_next()
                    self.assistant_log(f"Navigation Decision Result: {result}")
                except Exception as e:
                    self.assistant_log(f"ERROR: Navigation Decision Failure, attempting retry [ {depth} ]: {str(e)}")
                    return await navigate_to_next_page_async(previous_decision, depth + 1)
            try:
                call_result = await self.parse_and_call_function_async(result)
                self.assistant_log(f"Navigation Call Result: {call_result}")
                if type(call_result) == ToolResult:
                    url_navigated_to = call_result.url
                    self.tool_result_log.append(f"""
                    We just visited: {url_navigated_to}
                        Where should we go next?
                    """)
                return self.import_new_data(call_result)
            except Exception as e:
                self.assistant_log(f"ERROR: Function Call Failed, attempting retry [ {depth} ]: {str(e)}")
                return await navigate_to_next_page_async(previous_decision, depth + 1)

        urls = await self.get_set_recon_urls_async()

        async with self.state_context(AgentState.RUNNING):
            while (recon_step_count < recon_steps):
                recon_step_count += 1
                self.assistant_log(f"Executing recon step {recon_step_count}/{recon_steps}")
                await navigate_to_next_page_async()
                self.assistant_log(f"Recon Step {recon_step_count}: {str(self.get_last_item_in_data())}")


    async def run(self, request: Optional[str] = None) -> str:
        self.state = AgentState.RUNNING

        """
        objectives..
        first objective..
        required data..
        response format..
        
        + Generate 'Objective' or 'Objectives' per request?
            - Objective = Create a single objective to achieve.
            - Objectives = Create a list of objectives to achieve.
            
        + Generate a 'step plan' or 'step next' per objective ?
            - Step Plan = Create a chain of steps to achieve.
            - Step Next = Create a single next step to achieve.
            
        + How do we validate we've accomplished the goal?
        + 'Think' function that only summarizes results as we go...
            - See if the 'thoughts' have the answer we are looking for?
        
        TODO:
        [ URL ]
        1. extract input fields
        2. extract buttons
        3. extract html
        4. extract page contents
        
        - 
        """
        # if request: self.update_memory("user", request)
        await self.setup_assistant(user_request=request)
        await self.get_set_objective_async()
        await self.get_set_plan_async()

        await self.recon_mode()

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (self.current_step_count < self.max_steps and self.state != AgentState.FINISHED):
                if self.current_step_count >= 2:
                    self.ask_if_objective_is_completed()
                    if self.objective_is_complete:
                        self.state = AgentState.FINISHED
                        break

                step: NextStepModel = await self.get_set_next_step_async()

                self.current_step_count += 1
                self.assistant_log(f"Executing step {self.current_step_count}/{self.max_steps}")
                await self.make_action_async(step.next_step_or_action)
                self.steps_taken.append(step)
                results.append(f"Step {self.current_step_count}: {str(self.get_last_item_in_data())}")

            if self.current_step_count >= self.max_steps:
                self.current_step_count = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        resp = self.respond()
        return resp

    async def format_html_element_async(self, html: str):
        result = await self.llm().formatter_async(
            text=html,
            model=HtmlDecisionElement,
            system=f"""
                1. You parse html string data.
                2. Extract all Input Fields and Button Elements.
                3. Decide which element to use to accomplish the objective.
                <USER_REQUEST>
                    {self.user_request_prompt}
                </USER_REQUEST>
                <OBJECTIVE>
                    {self.overall_objective}
                    {self.current_step}
                </OBJECTIVE>
            """,
        )
        return result
    async def get_set_objective_async(self):
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
    async def get_set_plan_async(self):
        result = await self.llm().generate_async(
            user=self.user_request_prompt,
            system=f"""
                **Based on the objective and the user prompt, develop a plan on how to accomplish the users request/objective.**
                **Ignore requesting for more information, work with what you have, plan can be updated as we go.**
                
                <TOOLS_AVAILABLE>
                    {self.map_external_class()}
                </TOOLS_AVAILABLE>
                
                <OBJECTIVE>
                    {self.overall_objective}
                </OBJECTIVE>
            """,
        )

        if result:
            self.overall_plan = result

        return result
    def get_steps_taken_str(self) -> str:
        return "\n".join([
            f"""
                <STEP_ACTION>\n{str(step.next_step_or_action)}\n</STEP_ACTION>
            """
            for step in self.steps_taken
        ])
    async def get_set_next_step_async(self) -> Optional[NextStepModel]:
        result = await self.llm().formatter_async(
            text=f"""
                <STEPS_TAKEN>
                    {self.get_steps_taken_str()}
                </STEPS_TAKEN>
            """,
            model=NextStepModel,
            system=f"""
                1. Analyze the users request, the objective and previous step/action taken.
                2. Review the tools available.
                3. Develop a single step/action to make next.
                
                <TOOLS_AVAILABLE>
                    {self.map_external_class()}
                </TOOLS_AVAILABLE>
                
                <OBJECTIVE>
                    {self.overall_objective}
                </OBJECTIVE>
                
                <PLAN>
                    {self.overall_plan}
                </PLAN>
                    
                    {self.initial_request_tagged}
            """,
        )

        if result:
            self.previous_step = self.current_step
            self.current_step = result or None

        return result or None



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