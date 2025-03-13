
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List, Type, Optional

from pydantic import BaseModel

from rai.agentic.ai_modules import rModule, mMap, mAssistLog, mData
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.ingest.utilities.TextUtils import TextProcessor

# ASSISTANT_LOG_CHAIN is assumed to be defined globally
ASSISTANT_LOG_CHAIN = []

class rAssistantReasoningPlugin(rModule, mMap, mData, mAssistLog, ABC):
    """
    A reasoning assistant plugin that coordinates the process of generating plans,
    selecting functions to call, and ultimately driving the agent's behavior.
    Extend this abstract class to create specialized assistants.
    """
    assistant_system_prompt = ""
    user_request_prompt = ""

    assistant_objective = "Unknown Objective"
    ext_documentation_tagged = "<ExternalDocumentation> </ExternalDocumentation>"
    int_documentation_tagged = "<InternalDocumentation> </InternalDocumentation>"
    assistant_rules_tagged = f"<RULES> </RULES>"
    attached_data_tagged = f"<ATTACHED DATA> </ATTACHED DATA>"
    initial_request_tagged = f"<USER REQUEST> </USER REQUEST>"

    _data = {}

    def update_latest_data(self, **data): self.data.update(**data)

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
        """
        Construct and return the prompt used to decide the best function/tool to select.
        """
        return f"""
        Based on the User Prompt below, determine the best Function/Tool to select and call.
            <External Class Documentation>
            {self.map_external_class()}
            </External Class Documentation>
            <External Assistant Rules>
            {self.assistant_rules()}
            </External Assistant Rules>
            <ASSISTANT LOG>
            {self.get_assistant_log_str()}
            </ASSISTANT LOG>
        """
    def external_plan_prompt(self) -> str:
        return self.chain_data(
            self.ext_documentation_tagged,
            self.assistant_rules_tagged,
            self.attached_data_tagged,
            self.data,
            self.initial_request_tagged
        )

    """ REASONING ENGINE FUNCTIONALITY """
    def ask_ai_to_decide_which_function_to_call(self, user_prompt: str) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_external_json_tools()
            self.assistant_log("Attempting to decide on a function.")
            decision = self.rAI().generate_function(
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
            response = rTextTools.tool(
                name="is_true",
                user_prompt=self.chain_data(self.get_assistant_log_str(), self.assistant_objective),
                system_prompt="Based on the data provided, have we completed the objective?",
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
            response = rTextTools.tool(
                name="is_true",
                user_prompt=self.get_assistant_log_str(),
                system_prompt="Based on the assistant process log provided, do we retry the previous function call/action?",
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
                self.data,
                self.initial_request_tagged,
            )
            response = self.rAI().generate(
                user=final_response_request,
                system="Based on the data provided, create the appropriate response to send back to the user."
            )
            self.assistant_log("Final Response Generated", response)
            return f"<FINAL RESPONSE>\n{response}\n</FINAL RESPONSE>"
        except Exception as e:
            return self.assistant_error_log(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")

    def reason(self, user_request: str, **attached_data) -> Any:
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
            # The Assistant Process Log
            self.assistant_log("Started reasoning for user request.")
            self.assistant_log("Gathering and formatting data for reasoning.")

            # Assistant Rules Data
            self.ext_documentation_tagged = self.map_external_class()
            self.assistant_rules_tagged = self.tag_data("RULES", self.assistant_rules())
            self.assistant_system_prompt = self.tag_data(
                "ASSISTANT_RULES_AND_INFO",
                self.chain_data(self.ext_documentation_tagged, self.assistant_rules())
            )

            # User Request Data
            self.attached_data_tagged = self.tag_data("ATTACHED_DATA", attached_data)
            self.initial_request_tagged = self.tag_data("INITIAL_REQUEST", user_request)
            self.user_request_prompt = self.tag_data(
                "USER_REQUEST_PROMPT",
                f"{self.attached_data_tagged}\n{self.initial_request_tagged}"
            )

            # Establish the objective.
            self.assistant_objective = self.ask_ai_to_establish_objective()

            # Initialize the step/action queue.
            max_steps = 10
            step_queue = deque(self.ask_ai_to_generate_a_request_plan() or [])
            steps_taken = 0

            def make_action(action):
                self.assistant_log(f"Action to make: {action}")
                decision = self.ask_ai_to_decide_which_function_to_call(action)
                self.assistant_log(f"Function Call Decision: {decision}")
                if decision:
                    call_result = self.parse_and_call_function(decision)
                    if call_result: self.data = call_result
                    self.assistant_log(f"Function Call Result: {str(call_result)}")
                    return call_result
                self.assistant_error_log(f"Function Call Result: NONE")
                return None

            # Process the queue until it's empty or the objective is met.
            while step_queue:
                step = step_queue.popleft()
                steps_taken += 1
                try:
                    action = self.tag_data("ACTION", f"{steps_taken}.{step.step_action}")
                    make_action(action=action)
                    # Check if the objective is accomplished.
                    if self.ask_ai_if_objective_is_completed():
                        self.assistant_log(f"Objective completed on step [{steps_taken}]")
                        break
                    if self.ask_ai_if_action_needs_retry():
                        self.assistant_log(f"Determined action should be retried on step [{steps_taken}]")
                        make_action(action=action)
                        if self.ask_ai_if_objective_is_completed():
                            self.assistant_log(f"Objective completed on step [{steps_taken}]")
                            break
                    # handle error/no decision...
                except Exception as e:
                        self.assistant_error_log(f"Failed to complete step [{steps_taken}]", str(e))

                if max_steps < steps_taken: break

            # Final check for objective completion after processing the queue.
            self.assistant_log("Final objective completion check after empty queue.")
            final_response = self.ask_ai_to_generate_final_response()
            return self.AssistResponse(
                answer=final_response,
                data=self.data
            )
        except Exception as e:
            self.assistant_error_log(f"Overall Reasoning Error: [ {str(e)} ]")
            final_response = self.ask_ai_to_generate_final_response()
            return self.AssistResponse(
                answer=final_response,
                data=self.data
            )

