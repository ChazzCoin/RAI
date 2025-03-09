import json
import inspect
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List, Type, Union, get_origin, get_args, Callable, Optional

from F import LIST, DICT
from pydantic import BaseModel

from rai.agentic.ai_modules import rModule
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.ingest.utilities.TextUtils import TextProcessor

# ASSISTANT_LOG_CHAIN is assumed to be defined globally
ASSISTANT_LOG_CHAIN = []

class rAssistantReasoningPlugin(rModule, ABC):
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

    @staticmethod
    def tag_data(tag, data): return f"<{tag}>\n {data} \n</{tag}"

    data = {}

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

    @classmethod
    def ask(cls, user_prompt: str, **kwargs) -> Any:
        """High-level entry point for processing a user prompt with attached data."""
        return cls().reason(user_prompt, **kwargs)

    @classmethod
    def assistant_log(cls, *data: str) -> str:
        """Log messages to the assistant log chain."""
        for line in data:
            info_message = "INFO: " + line
            print(f"r{cls.module_name()}", info_message)
            ASSISTANT_LOG_CHAIN.append(info_message)
        return str(data)

    @classmethod
    def assistant_error_log(cls, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix."""
        for line in data:
            error_message = "ERROR: " + line
            print(f"r{cls.module_name()}", error_message)
            ASSISTANT_LOG_CHAIN.append(error_message)
        return str(data)

    @staticmethod
    def get_assistant_log() -> List[str]:
        """Retrieve the assistant log as a list of strings."""
        return ASSISTANT_LOG_CHAIN

    @staticmethod
    def get_assistant_log_str() -> str:
        """Retrieve the assistant log as a single string."""
        return str(ASSISTANT_LOG_CHAIN)

    """ INTERNAL FUNCTIONS """
    @staticmethod
    def internal_assistant_rules() -> str:
        """Return the internal assistant rules as a string."""
        return """
            Analyze and Review the Process Logs.
            Review the internal functions.
            If INFO: validate or proceed forward 
            IF ERROR: attempt to retry or tell the user what the error is.
        """
    @staticmethod
    def map_internal_class() -> str:
        """
        Map all public callable functions of the class (excluding built-ins)
        and return a formatted string with their documentation.
        """
        if rAssistantReasoningPlugin.__name__ in ('object', 'ABC'):
            return ""
        doc_lines = [f"Internal/Child Class: {rAssistantReasoningPlugin.__name__}"]
        for name, member in inspect.getmembers(rAssistantReasoningPlugin, predicate=inspect.isfunction):
            if name.startswith("__"):
                continue  # Skip magic methods
            func_doc = inspect.getdoc(member) or "No documentation provided."
            doc_lines.append(f"\nFunction: {name}\nDocumentation: {func_doc}\n")
        doc_lines.append("-" * 40)
        return f"<Context> {' '.join(doc_lines)} <Context>\nCreate your plan based on the functions in the Context."
    @staticmethod
    def get_functions_for_internal_calls() -> List[Dict[str, Any]]:
        """
        Inspect the base class (rAssistantReasoningPlugin) for its public callable methods
        (excluding built-ins) and return a list of dictionaries formatted in a JSON-schema style.
        This mapping is intended for internal use.
        """
        functions = []
        base_cls = rAssistantReasoningPlugin
        for name, member in inspect.getmembers(base_cls, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue  # Skip internal or magic methods

            description = inspect.getdoc(member) or ""
            sig = inspect.signature(member)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                # Map Python type annotations to JSON Schema types.
                if param.annotation != inspect.Parameter.empty:
                    ann = param.annotation
                    if ann == int:
                        prop_schema = {"type": "integer"}
                    elif ann == float:
                        prop_schema = {"type": "number"}
                    elif ann == bool:
                        prop_schema = {"type": "boolean"}
                    elif ann == list:
                        prop_schema = {"type": "array"}
                    elif ann == dict:
                        prop_schema = {"type": "object"}
                    else:
                        prop_schema = {"type": "string"}
                else:
                    prop_schema = {"type": "string"}

                properties[param_name] = prop_schema

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            functions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                        "additionalProperties": False,
                    },
                },
            })
        return functions
    def get_internal_json_tools(self) -> List[Dict[str, Any]]:
        """Return a JSON representation of all tool-callable functions available on this instance."""
        self.assistant_log("Mapping Internal function tools.")
        return self.get_functions_for_internal_calls()
    def internal_decision_prompt(self) -> str:
        """Construct and return the prompt used to decide the best function/tool to select."""
        return f"""
        Based on the Assistants internal process logs and functionality, determine the best Function/Tool to select and call.
            <Internal Class Documentation>
            {self.map_internal_class()}
            </Internal Class Documentation>
            <Internal Assistant Rules>
            {self.internal_assistant_rules()}
            </Internal Assistant Rules>
        """

    """ EXTERNAL FUNCTIONS """
    def map_external_class(self) -> str:
        """
        Map all public callable functions of the class (excluding built-ins)
        and return a formatted string with their documentation.
        """
        if self.__class__.__name__ in ('object', 'ABC'):
            return ""
        doc_lines = [f"External/Parent Class: {self.__class__.__name__}"]
        for name, member in self.__class__.__dict__.items():
            if name.startswith("__"):
                continue  # Skip magic methods
            func_doc = inspect.getdoc(member) or "No documentation provided."
            doc_lines.append(f"\nFunction: {name}\nDocumentation: {func_doc}\n")
        doc_lines.append("-" * 40)
        return f"<External_Docs>\n {' '.join(doc_lines)} \n</External_Docs>\nCreate your plan based on the functions in the Documentation."
    @staticmethod
    def function_to_schema(func: Callable) -> Dict[str, Any]:
        """
        Convert a function to its JSON Schema representation with robust type handling,
        including support for union types (e.g., Optional types).
        """
        # Mapping from Python types to JSON Schema types.
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }

        try:
            sig = inspect.signature(func)
        except ValueError as e:
            return {
                "result": rAssistantReasoningPlugin.assistant_error_log(
                f"Failed to get signature for function {func.__name__}: {str(e)}")
            }

        properties: Dict[str, Any] = {}
        required: List[str] = []
        description = (inspect.getdoc(func) or "").strip()

        for param_name, param in sig.parameters.items():
            # Skip 'self' for instance methods.
            if param_name == "self":
                continue

            annotation = param.annotation
            if annotation != inspect.Parameter.empty:
                # Check for Union types (commonly used for Optional parameters)
                origin = get_origin(annotation)
                if origin is Union:
                    args = get_args(annotation)
                    # If it's Optional[T] (i.e. Union[T, None]), choose T.
                    non_none_types = [a for a in args if a is not type(None)]
                    if len(non_none_types) == 1:
                        annotation = non_none_types[0]
                    else:
                        # Fallback to string if multiple types remain.
                        annotation = str
                json_type = type_map.get(annotation, "string")
            else:
                json_type = "string"

            properties[param_name] = {"type": json_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": description,
                "parameters": parameters_schema,
            },
        }
    def get_external_json_tools(self) -> list[dict[str, Any]]:
        """
        Inspect the class for public callable methods and return a list of dictionaries,
        each formatted in a robust JSON Schema style for external calls.
        """
        functions = []
        # Iterate over only the methods defined in this class (parent) itself.
        for name, member in self.__class__.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(member, (staticmethod, classmethod)):
                func_obj = member.__func__
            elif inspect.isfunction(member):
                func_obj = member
            else:
                continue
            functions.append(self.function_to_schema(func_obj))
        return functions
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

    """ INTERNAL ENGINE FUNCTIONALITY """
    def parse_and_call_function(self, json_input: Union[str, dict, list]) -> Any:
        """
        Parse a JSON string/dict/list representing a function call with its arguments,
        then call the corresponding method.
        """
        try:
            # Normalize the input.
            if isinstance(json_input, list):
                try:
                    temp = LIST.get(0, json_input, "browse_documents")
                    data = DICT.get("function", temp, None)
                except Exception as e:
                    return self.assistant_error_log(f"Error processing list input: {e}")
            elif isinstance(json_input, str):
                try:
                    data = json.loads(json_input)
                except json.JSONDecodeError as e:
                    return self.assistant_error_log(f"Invalid JSON string: {e}")
            elif isinstance(json_input, dict):
                data = json_input
            else:
                return self.assistant_error_log("Input must be a JSON string, list, or dictionary.")

            # Extract function name.
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            if not func_name:
                return self.assistant_error_log("Missing function name ('name') in data.")

            # Extract and parse arguments.
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            if args_source is None:
                return self.assistant_error_log("Missing arguments ('arguments') in data.")

            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return self.assistant_error_log(f"Error decoding 'arguments': {e}")
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return self.assistant_error_log("Arguments must be a dictionary or a valid JSON string.")

            if not isinstance(arguments, dict):
                return self.assistant_error_log("Parsed arguments is not a dictionary.")

            # Ensure the function exists and is callable.
            if not hasattr(self, func_name):
                return self.assistant_error_log(f"Function '{func_name}' not found.")
            func = getattr(self, func_name)
            if not callable(func):
                return self.assistant_error_log(f"'{func_name}' is not callable.")

            self.assistant_log(f"Calling function '{func_name}' with arguments: {arguments}")
            return func(**arguments)
        except Exception as e:
            return self.assistant_error_log(f"Error in parse_and_call: {json_input} | Exception: {e}")
    def decide_function(self, user_prompt: str) -> Any:
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

    def decide_and_call(self, user_prompt):
        decision_prompt = self.chain_data(self.assistant_objective, self.data, user_prompt)
        result = self.decide_function(decision_prompt)
        call_result = self.parse_and_call_function(result)
        self.assistant_log(f"Functon Call Result: [ {call_result} ]")
        return call_result

    def ask_master_assistant(self, user_prompt: str) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_external_json_tools()
            self.assistant_log("Asking 'Master' Assistant.")
            response = self.rAI().generate_function(
                user=user_prompt,
                system=self.chain_data(self.assistant_system_prompt, self.assistant_objective),
                functions=tools,
                raw_result=True
            )
            self.assistant_log(f"Master Assistant Says: [ {response} ]")
            return response
        except Exception as e:
            return self.assistant_error_log("Error in deciding function:", str(e))

    def attempt_to_get_latest_external_data(self) -> Any:
        """Decide the function to call and get the latest data."""
        try:
            tools = self.get_external_json_tools()
            self.assistant_log("Attempting to retrieve the latest data.")
            decision = self.rAI().generate_function(
                user="call the function to grab the latest 'core' data ",
                system=self.external_decision_prompt(),
                functions=tools,
                raw_result=True
            )
            self.assistant_log(f"Decision made: [ {decision} ]")
            if decision:
                data = self.parse_and_call_function(decision)
                return f"<LATEST EXTERNAL DATA>\n {data} \n</LATEST EXTERNAL DATA>"
        except Exception as e:
            return self.assistant_error_log("Error in deciding function:", str(e))
    def generate_required_data_objects(self, user_prompt: str) -> Any:
        """AI CALL: Generate required data objects according to the required model."""
        try:
            model_dump = self._required_model().model_dump()
            self.assistant_log(f"Generating required object. {model_dump}")
            response = self.rAI().generate_format(
                user=user_prompt,
                system="Extract the appropriate data according to the format model provided.",
                format=self._required_model()
            )
            self.assistant_log(f"Generated required object. {response}")
            return response
        except Exception as e:
            return self.assistant_error_log("Failed to generate the required data objects.", str(e))
    def check_if_objective_completed(self) -> bool:
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

    def check_if_action_needs_retry(self) -> bool:
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
    def generate_external_plan(self) -> List[Any]:
        """AI CALL: Generate a chain-of-steps plan based on the provided prompt."""
        try:
            steps = rTextTools.tool("chain-of-steps", TextProcessor.NORMALIZER(self.external_plan_prompt()))
            plan = [f"<ACTION> {step.order_index}. {step.step_action} </ACTION>" for step in steps]
            self.assistant_log("\nGenerated the following Action Plan\n", "\n".join(plan))
            return steps
        except Exception as e:
            self.assistant_error_log("Failed to generate a plan.", str(e))
            return []

    def generate_next_step(self) -> Optional[str]:
        """AI CALL: Generate a chain-of-steps plan based on the provided prompt."""
        try:
            step = rTextTools.tool("next-step", TextProcessor.NORMALIZER(self.next_step_prompt()))
            step_tagged = f"<ACTION> {step} </ACTION>"
            self.assistant_log(f"\nGenerated the following Action Plan\n [ {step_tagged} ]")
            return step_tagged
        except Exception as e:
            return self.assistant_error_log(f"Failed to generate a plan. [ {str(e)} ]")

    def attempt_to_establish_objective(self) -> str:
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
    def generate_final_response(self) -> str:
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

    def external_plan_prompt(self) -> str:
        return self.chain_data(
            self.ext_documentation_tagged,
            self.assistant_rules_tagged,
            self.attached_data_tagged,
            self.data,
            self.initial_request_tagged
        )
    def next_step_prompt(self) -> str:
        return self.chain_data(
            self.ext_documentation_tagged,
            self.assistant_rules_tagged,
            self.get_assistant_log_str(),
            self.assistant_objective
        )

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
            self.assistant_objective = self.attempt_to_establish_objective()

            # Initialize the step/action queue.
            max_steps = 10
            step_queue = deque(self.generate_external_plan() or [])
            steps_taken = 0

            def make_action(action):
                self.assistant_log(f"Action to make: {action}")
                decision = self.decide_function(action)
                self.assistant_log(f"Function Call Decision: {decision}")
                if decision:
                    call_result = self.parse_and_call_function(decision)
                    self.assistant_log(f"Function Call Result: {str(call_result)}")
                    return call_result
                self.assistant_error_log(f"Function Call Result: NONE")
                return None

            # Process the queue until it's empty or the objective is met.
            while step_queue:
                step = step_queue.popleft()
                steps_taken += 1
                try:
                    action = f"<ACTION> {steps_taken}.{step.step_action} </ACTION>"
                    make_action(action=action)
                    # Check if the objective is accomplished.
                    if self.check_if_objective_completed():
                        self.assistant_log(f"Objective completed on step [{steps_taken}]")
                        break
                    if self.check_if_action_needs_retry():
                        self.assistant_log(f"Determined action should be retried on step [{steps_taken}]")
                        make_action(action=action)
                        if self.check_if_objective_completed():
                            self.assistant_log(f"Objective completed on step [{steps_taken}]")
                            break
                    # handle error/no decision...
                except Exception as e:
                        self.assistant_error_log(f"Failed to complete step [{steps_taken}]", str(e))

                if max_steps < steps_taken: break

            # Final check for objective completion after processing the queue.
            self.assistant_log("Final objective completion check after empty queue.")
            return self.generate_final_response()
        except Exception as e:
            self.assistant_error_log("Error in reason:", str(e))
            return self.generate_final_response()
