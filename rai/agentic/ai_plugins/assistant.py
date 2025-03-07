import json
import inspect
from abc import abstractmethod
from typing import List, Type

from F import LIST, DICT
from pydantic import BaseModel

from rai.agentic.ai_modules import rModule
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.agentic.ai_tools.text_tools.text_formats import ChainedStepModel
from rai.ingest.utilities.TextUtils import TextProcessor


class rAssistantPlugin(rModule):

    def __init__(self): super().__init__()

    @classmethod
    def ask(cls, user_prompt, **kwargs):
        return cls().decide_and_call(user_prompt, **kwargs)

    def get_functions_map(self):
        """
        Inspect the class for callable public methods (excluding methods starting with an underscore)
        and returns a list of dictionaries for each function formatted in a JSON-schema style:

        {
          "type": "function",
          "function": {
              "name": <function name>,
              "description": <function docstring>,
              "parameters": {
                  "type": "object",
                  "properties": { ... },
                  "required": [ ... ],
                  "additionalProperties": False,
              },
          },
        }
        """
        functions = []
        # Inspect the class to include static methods.
        for name, member in inspect.getmembers(self.__class__, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue  # Skip private or built-in methods

            # Use the function's docstring as its description.
            description = inspect.getdoc(member) or ""
            sig = inspect.signature(member)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Static methods do not have a "self" parameter.
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

                # Mark parameters with no default as required.
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            function_json = {
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
            }
            functions.append(function_json)
        return functions
    def get_json_tools(self) -> [dict]:
        """
        Returns a JSON string that describes all tool-callable functions available on this instance.
        The output can be sent to an AI tool to describe what function calls are available.
        """
        return self.get_functions_map()
    def system_prompt(self):
        return """
            Based on the User Prompt below, determine the best Function/Tool to select and call.
        """
    def parse_and_call(self, json_str):
        """
        Parses a JSON string representing a function call and its arguments, then calls the corresponding method.

        Expected JSON format:
        {
          "name": "function_name",
          "arguments": {
              "param1": value1,
              "param2": value2,
              ...
          }
        }

        Returns the result of the function call.
        """
        try:
            # Support multiple types of input for robustness:
            # 1. If json_str is a list, use the legacy code path.
            if isinstance(json_str, list):
                try:
                    temp = LIST.get(0, json_str, "browse_documents")
                    data = DICT.get("function", temp, None)
                except Exception as e:
                    raise ValueError("Error processing list input using LIST/DICT utilities.") from e
            # 2. If json_str is a str, assume it's a JSON string and parse it.
            elif isinstance(json_str, str):
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    raise ValueError("Provided string is not valid JSON.") from e
            # 3. If already a dict, use it directly.
            elif isinstance(json_str, dict):
                data = json_str
            else:
                raise TypeError("Input must be a JSON string, list, or dictionary.")

            # Extract function name using attribute access if available, otherwise dict key.
            if hasattr(data, 'name'):
                func_name = data.name
            elif isinstance(data, dict) and 'name' in data:
                func_name = data['name']
            else:
                raise KeyError("Missing function name ('name') in the provided data.")

            # Extract arguments from the data
            if hasattr(data, 'arguments'):
                args_source = data.arguments
            elif isinstance(data, dict) and 'arguments' in data:
                args_source = data['arguments']
            else:
                raise KeyError("Missing arguments ('arguments') in the provided data.")

            # If arguments are provided as a JSON string, parse them.
            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    raise ValueError("Error decoding the 'arguments' JSON string.") from e
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                raise ValueError(
                    "Arguments must be either a dictionary or a valid JSON string representing a dictionary.")

            # Final check: arguments must be a dict.
            if not isinstance(arguments, dict):
                raise ValueError("The parsed 'arguments' is not a dictionary.")

            # Ensure the function exists on the instance
            if not hasattr(self, func_name):
                raise AttributeError(f"Function '{func_name}' not found on the instance.")
            func = getattr(self, func_name)
            if not callable(func):
                raise AttributeError(f"'{func_name}' is not callable.")

            # Call the function with the provided arguments.
            return func(**arguments)

        except Exception as e:
            # Here you might want to log the error details in a production environment.
            raise e
    def decide_function(self, user_prompt):
        tools = self.get_json_tools()
        decision = self.rAI().generate_function(
            user=user_prompt,
            system=self.system_prompt(),
            functions=tools,
            raw_result=True
        )
        print("Curator Decision:", decision)
        return decision
    def decide_and_call(self, user_prompt, **kwargs):
        merged_user_prompt = f"Attached Data: {kwargs}\nUser Prompt: {user_prompt}"
        result = self.decide_function(merged_user_prompt)
        call_result = self.parse_and_call(result)
        print("Curator Functon Call Result:", call_result)
        return call_result

ASSISTANT_LOG_CHAIN = []

import json
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union
from pydantic import BaseModel

# Assume these external objects exist:
# - ASSISTANT_LOG_CHAIN (a global list)
# - rTextTools, rAI, and rModule (base class or external dependencies)

class rAssistantReasoningPlugin(rModule, ABC):
    """
    A reasoning assistant plugin that coordinates the process of generating plans,
    selecting functions to call, and ultimately driving the agent's behavior.
    Extend this abstract class to create specialized assistants.
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def assistant_rules() -> str:
        """
        Return the assistant rules as a string.
        """
        pass

    @staticmethod
    @abstractmethod
    def required_model() -> Type[BaseModel]:
        """
        Return the required data model for the assistant.
        """
        pass

    @classmethod
    def ask(cls, user_prompt: str, **kwargs) -> Any:
        """
        High-level entry point for processing a user prompt with attached data.
        """
        return cls().reason(user_prompt, **kwargs)

    @staticmethod
    def assistant_log(*data: str) -> str:
        """
        Log messages to the assistant log chain.
        """
        for line in data:
            print("r", line)
            ASSISTANT_LOG_CHAIN.append(line)
        return str(data)

    @staticmethod
    def get_assistant_log() -> List[str]:
        """
        Retrieve the assistant log as a list of strings.
        """
        return ASSISTANT_LOG_CHAIN

    @staticmethod
    def get_assistant_log_str() -> str:
        """
        Retrieve the assistant log as a single string.
        """
        return str(ASSISTANT_LOG_CHAIN)

    @staticmethod
    def chain_data(*args: Any) -> str:
        """
        Join provided arguments into a single string. This override ensures that non-string
        types (like StateObject) are converted to strings before joining.
        """
        return "\n".join(str(arg) for arg in args)

    @classmethod
    def map_class(cls) -> str:
        """
        Map all public callable functions of the class (excluding built-ins)
        and return a formatted string with their documentation.
        """
        if cls.__name__ in ('object', 'ABC'):
            return ""
        doc_lines = [f"Parent Class: {cls.__name__}"]
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("__"):
                continue  # Skip magic methods
            func_doc = inspect.getdoc(member) or "No documentation provided."
            doc_lines.append(f"\nFunction: {name}\nDocumentation: {func_doc}\n")
        doc_lines.append("-" * 40)
        return f"<Context> {' '.join(doc_lines)} <Context>\nCreate your plan based on the functions in the Context."

    def get_functions_map(self) -> List[Dict[str, Any]]:
        """
        Inspect the class for public callable methods and return a list of dictionaries,
        each formatted in a JSON-schema style.
        """
        functions = []
        for name, member in inspect.getmembers(self.__class__, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue

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

    def get_json_tools(self) -> List[Dict[str, Any]]:
        """
        Return a JSON representation of all tool-callable functions available on this instance.
        """
        self.assistant_log("Mapping function tools.")
        return self.get_functions_map()

    def decision_prompt(self) -> str:
        """
        Construct and return the prompt used to decide the best function/tool to select.
        """
        return f"""
            Based on the User Prompt below, determine the best Function/Tool to select and call.
            <Function Options>
            {self.map_class()}
            </Function Options>
            {self.assistant_rules()}
        """

    def parse_and_call(self, json_input: Union[str, dict, list]) -> Any:
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
                    return self.assistant_log(f"Error processing list input: {e}")
            elif isinstance(json_input, str):
                try:
                    data = json.loads(json_input)
                except json.JSONDecodeError as e:
                    return self.assistant_log(f"Invalid JSON string: {e}")
            elif isinstance(json_input, dict):
                data = json_input
            else:
                return self.assistant_log("Input must be a JSON string, list, or dictionary.")

            # Extract function name.
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            if not func_name:
                return self.assistant_log("Missing function name ('name') in data.")

            # Extract and parse arguments.
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            if args_source is None:
                return self.assistant_log("Missing arguments ('arguments') in data.")

            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return self.assistant_log(f"Error decoding 'arguments': {e}")
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return self.assistant_log("Arguments must be a dictionary or a valid JSON string.")

            if not isinstance(arguments, dict):
                return self.assistant_log("Parsed arguments is not a dictionary.")

            # Ensure the function exists and is callable.
            if not hasattr(self, func_name):
                return self.assistant_log(f"Function '{func_name}' not found.")
            func = getattr(self, func_name)
            if not callable(func):
                return self.assistant_log(f"'{func_name}' is not callable.")

            self.assistant_log(f"Calling function '{func_name}' with arguments: {arguments}")
            return func(**arguments)
        except Exception as e:
            return self.assistant_log(f"Error in parse_and_call: {json_input} | Exception: {e}")

    def decide_function(self, user_prompt: str) -> Any:
        """
        Generate a decision on which function/tool to call based on the user prompt.
        """
        tools = self.get_json_tools()
        self.assistant_log("Attempting to decide on a function.")
        decision = self.rAI().generate_function(
            user=user_prompt,
            system=self.decision_prompt(),
            functions=tools,
            raw_result=True
        )
        self.assistant_log("Decision made:", decision)
        return decision

    def decide(self, user_prompt: str, **attached_data) -> Any:
        """
        High-level method that merges user prompt and attached data, then selects and calls the appropriate function.
        """
        merged_prompt = f"Attached Data: {attached_data}\nUser Prompt: {user_prompt}"
        decision = self.decide_function(merged_prompt)
        call_result = self.parse_and_call(decision)
        self.assistant_log("Function call result:", call_result)
        return call_result

    @staticmethod
    def generate_required_data_objects(user_prompt: str) -> Any:
        """
        Generate required data objects according to the required model.
        """
        model_dump = rAssistantReasoningPlugin.required_model().model_dump()
        rAssistantReasoningPlugin.assistant_log("Generating required object.", model_dump)
        response = rAssistantReasoningPlugin.rAI().generate_format(
            user=user_prompt,
            system="Extract the appropriate data according to the format model provided.",
            format=rAssistantReasoningPlugin.required_model()
        )
        rAssistantReasoningPlugin.assistant_log("Generated required object.", response)
        return response

    @staticmethod
    def check_if_objective_completed(prompt: str) -> bool:
        """
        Check whether the objective has been completed based on the given prompt.
        """
        rAssistantReasoningPlugin.assistant_log("Checking if objective has been completed.")
        response = rTextTools.tool(
            name="is_true",
            user_prompt=prompt,
            system_prompt="Based on the data provided, have we completed the objective for the User Prompt?",
        )
        rAssistantReasoningPlugin.assistant_log("Objective completion check:", response)
        return response

    @staticmethod
    def generate_step_by_step_plan(prompt: str) -> List[Any]:
        """
        Generate a chain-of-steps plan based on the provided prompt.
        """
        steps = rTextTools.tool("chain-of-steps", TextProcessor.NORMALIZER(prompt))
        plan = [f"<Action> {step.order_index}. {step.step_action} <Action>" for step in steps]
        rAssistantReasoningPlugin.assistant_log("Generated plan steps:", "\n".join(plan))
        return steps

    @staticmethod
    def attempt_to_complete_objective(prompt: str) -> str:
        """
        Attempt to complete the objective based on the provided prompt.
        """
        rAssistantReasoningPlugin.assistant_log(f"Attempting to complete objective.")
        response = rTextTools.tool(
            "complete-objective",
            user_prompt=rAssistantReasoningPlugin.chain_data(
                rAssistantReasoningPlugin.get_assistant_log_str(), prompt
            )
        )
        if response: rAssistantReasoningPlugin.assistant_log(f"Objective completed: {response}")
        else: rAssistantReasoningPlugin.assistant_log(f"Objective not completed: {response}")
        return response

    @staticmethod
    def attempt_to_establish_objective(prompt: str) -> str:
        """
        Attempt to establish an objective based on the provided prompt.
        """
        rAssistantReasoningPlugin.assistant_log(f"Attempting to establish objective: {prompt}")
        response = rTextTools.tool(
            "objective-summary",
            user_prompt=rAssistantReasoningPlugin.chain_data(
                rAssistantReasoningPlugin.map_class(), prompt
            )
        )
        rAssistantReasoningPlugin.assistant_log(f"Established objective: {response}")
        return response

    def reason(self, user_request: str, **attached_data) -> Any:
        """
        Main reasoning method that:
          1. Gathers and formats context, rules, and attached data.
          2. Establishes the objective.
          3. Generates and processes a step-by-step plan.
          4. Checks for objective completion.
        """
        self.assistant_log("Gathering and formatting data for reasoning.")
        documentation = self.map_class()
        rules = f"\n<Rules> {self.assistant_rules()} </Rules>\n"
        attached_data_str = f"\n<Attached Data> {attached_data} </Attached Data>\n"
        request_str = f"\n<User Request> {user_request} </User Request>\n"
        plan_request = self.chain_data(documentation, rules, attached_data_str, request_str)

        # Establish the objective.
        objective_summary = self.attempt_to_establish_objective(plan_request)
        objective_request = self.chain_data(objective_summary, rules, request_str)

        # Generate and process the plan.
        steps: List[Any] = self.generate_step_by_step_plan(plan_request)
        for step in steps:
            try:
                action = f"<Action> {step.step_action} </Action>"
                self.assistant_log("Processing step action:", action)
                decision = self.decide_function(f"{attached_data_str}\n{action}\n{request_str}")
                if decision:
                    call_result = self.parse_and_call(decision)

                    # Check for objective completion.
                    if self.check_if_objective_completed(self.chain_data(call_result, request_str)):
                        obj_result = self.attempt_to_complete_objective(
                            self.chain_data(objective_request, call_result)
                        )
                        self.assistant_log("Objective completed.", obj_result)
                        return obj_result, self.get_assistant_log_str()

                    self.assistant_log("Step completed.", call_result)
            except Exception as e:
                self.assistant_log("Error in step:", str(e))
                continue

        # Final check for objective completion.
        obj_result = self.attempt_to_complete_objective(
            self.chain_data(objective_request, request_str)
        )
        self.assistant_log("Final objective completion.", obj_result)
        return obj_result, self.get_assistant_log_str()


class rAssistantReasoningPlugin2(rModule):

    def __init__(self): super().__init__()

    @staticmethod
    @abstractmethod
    def assistant_rules() -> str: pass

    @staticmethod
    @abstractmethod
    def required_model() -> Type[BaseModel]:
        """ The Required Data Model for the Parent Class """
        pass

    @classmethod
    def ask(cls, user_prompt, **kwargs):
        return cls().reason(user_prompt, **kwargs)

    @staticmethod
    def assistant_log(*data:str):
        for line in data:
            print("r", line)
            ASSISTANT_LOG_CHAIN.append(line)
        return data

    @staticmethod
    def get_assistant_log() -> list: return ASSISTANT_LOG_CHAIN
    @staticmethod
    def get_assistant_log_str() -> str: return str(ASSISTANT_LOG_CHAIN)
    @classmethod
    def map_class(cls) -> str:
        """ Maps all callable functions of the parent class (excluding built-ins)"""
        doc_string = ""
        if cls.__name__ in ('object', 'ABC'): return ""
        doc_string += f"Parent Class: {cls.__name__}\n"
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("__"): continue  # Skip special/magic methods
            func_doc = inspect.getdoc(member) or "No documentation provided."
            doc_string += f"\nFunction: {name}\nDocumentation: {func_doc}\n"
        doc_string += "\n" + ("-" * 40) + "\n\n"
        return f"""
            <Context> {doc_string} <Context>
            Create your plan based on the functions in the Context.
        """

    def get_functions_map(self):
        """
        Inspect the class for callable public methods (excluding methods starting with an underscore)
        and returns a list of dictionaries for each function formatted in a JSON-schema style:

        {
          "type": "function",
          "function": {
              "name": <function name>,
              "description": <function docstring>,
              "parameters": {
                  "type": "object",
                  "properties": { ... },
                  "required": [ ... ],
                  "additionalProperties": False,
              },
          },
        }
        """
        functions = []
        # Inspect the class to include static methods.
        for name, member in inspect.getmembers(self.__class__, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue  # Skip private or built-in methods

            # Use the function's docstring as its description.
            description = inspect.getdoc(member) or ""
            sig = inspect.signature(member)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Static methods do not have a "self" parameter.
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

                # Mark parameters with no default as required.
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            function_json = {
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
            }
            functions.append(function_json)
        return functions
    def get_json_tools(self) -> [dict]:
        """
        Returns a JSON string that describes all tool-callable functions available on this instance.
        The output can be sent to an AI tool to describe what function calls are available.
        """
        self.assistant_log("Reasoning Assistant is mapping Function Tools.")
        return self.get_functions_map()
    def decision_prompt(self):
        return f"""
            Based on the User Prompt below, determine the best Function/Tool to select and call.
            <Function Options>
            {self.map_class()}
            </Function Options>
            {self.assistant_rules()}
        """
    def parse_and_call(self, json_str):
        """Parses a JSON string representing a function call and its arguments, then calls the corresponding method."""
        try:
            # Support multiple types of input for robustness:
            # 1. If json_str is a list, use the legacy code path.
            if isinstance(json_str, list):
                try:
                    temp = LIST.get(0, json_str, "browse_documents")
                    data = DICT.get("function", temp, None)
                except Exception as e:
                    return self.assistant_log(f"Error processing list input using LIST/DICT utilities. {e}")
            # 2. If json_str is a str, assume it's a JSON string and parse it.
            elif isinstance(json_str, str):
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    return self.assistant_log(f"Provided string is not valid JSON. {e}")
            # 3. If already a dict, use it directly.
            elif isinstance(json_str, dict):
                data = json_str
            else:
                return self.assistant_log("Input must be a JSON string, list, or dictionary.")

            # Extract function name using attribute access if available, otherwise dict key.
            if hasattr(data, 'name'):
                func_name = data.name
            elif isinstance(data, dict) and 'name' in data:
                func_name = data['name']
            else:
                return self.assistant_log("Missing function name ('name') in the provided data.")

            # Extract arguments from the data
            if hasattr(data, 'arguments'):
                args_source = data.arguments
            elif isinstance(data, dict) and 'arguments' in data:
                args_source = data['arguments']
            else:
                return self.assistant_log("Missing arguments ('arguments') in the provided data.")

            # If arguments are provided as a JSON string, parse them.
            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return self.assistant_log(f"Error decoding the 'arguments' JSON string. {e}")
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return self.assistant_log("Arguments must be either a dictionary or a valid JSON string representing a dictionary.")
            # Final check: arguments must be a dict.
            if not isinstance(arguments, dict):
                return self.assistant_log("The parsed 'arguments' is not a dictionary.")
            # Ensure the function exists on the instance
            if not hasattr(self, func_name):
                return self.assistant_log(f"Function '{func_name}' not found on the instance.")
            func = getattr(self, func_name)
            if not callable(func):
                return self.assistant_log(f"'{func_name}' is not callable.")
            # Call the function with the provided arguments.
            self.assistant_log(f"parse_and_call: Running function '{func_name}' with arguments: {arguments}")
            return func(**arguments)
        except Exception as e:
            return self.assistant_log(f"Reasoning Assistant has encountered an ERROR attempting to call function. \n [ {json_str} ] \n [ {e} ]")

    def decide_function(self, user_prompt):
        tools = self.get_json_tools()
        self.assistant_log("Reasoning Assistant is attempting to make a decision.")
        decision = self.rAI().generate_function(
            user=user_prompt,
            system=self.decision_prompt(),
            functions=tools,
            raw_result=True
        )
        self.assistant_log("Reasoning Assistant Decision:", decision)
        return decision

    def decide(self, user_prompt, **attached_data):
        merged_user_prompt = f"Attached Data: {attached_data}\nUser Prompt: {user_prompt}"
        result = self.decide_function(merged_user_prompt)
        call_result = self.parse_and_call(result)
        self.assistant_log("Reasoning Assistant Functon Call Result:", call_result)
        return call_result

    @staticmethod
    def generate_required_data_objects(user_prompt):
        rAssistantReasoningPlugin.assistant_log("Reasoning Assistant is attempting to generate required object.", rAssistantReasoningPlugin.required_model().model_dump())
        response = rAssistantReasoningPlugin.rAI().generate_format(
            user=user_prompt,
            system="Extract the appropriate data according to the format model provided.",
            format=rAssistantReasoningPlugin.required_model()
        )
        rAssistantReasoningPlugin.assistant_log("Reasoning Assistant has generate required object.", response)
        return response

    @staticmethod
    def check_if_objective_been_completed(prompt) -> bool:
        rAssistantReasoningPlugin.assistant_log("Reasoning Assistant is checking is the objective has been completed.")
        response = rTextTools.tool(
            name="is_true",
            user_prompt=prompt,
            system_prompt="Based on the data provided, have we completed the objective for the User Prompt?",
        )
        rAssistantReasoningPlugin.assistant_log("Reasoning Assistant has determined objective completion is:", response)
        return response

    @staticmethod
    def generate_step_by_step_plan(prompt) -> List[ChainedStepModel]:
        steps = rTextTools.tool("chain-of-steps", prompt)
        plan = []
        for step in steps:
            plan.append(f"<Action> {step.order_index}. {step.step_action} <Action>")
        rAssistantReasoningPlugin.assistant_log("Reasoning Plan:", "\n".join(plan))
        return steps

    @staticmethod
    def attempt_to_complete_objective(prompt) -> str:
        rAssistantReasoningPlugin.assistant_log(f"Attempting to Complete Objective: {prompt}")
        response = rTextTools.tool("complete-objective", user_prompt=rAssistantReasoningPlugin.chain_data(rAssistantReasoningPlugin.get_assistant_log_str(), prompt))
        rAssistantReasoningPlugin.assistant_log(f"Completed Objective: {response}")
        return response

    @staticmethod
    def attempt_to_establish_objective(prompt) -> str:
        rAssistantReasoningPlugin.assistant_log(f"Attempting to Establish Objective: {prompt}")
        response = rTextTools.tool("objective-summary", user_prompt=rAssistantReasoningPlugin.chain_data(rAssistantReasoningPlugin.map_class(), prompt))
        rAssistantReasoningPlugin.assistant_log(f"Completed Establishing Objective: {response}")
        return response

    def reason(self, user_request, **attached_data):

        self.assistant_log("Reasoning Assistant is gathering and formatting appropriate data.")
        attached_documentation = self.map_class()
        attached_rules = f"\n <Rules> {self.assistant_rules()} \n <Rules> \n"
        attached_data = f"\n <Attached Data> {attached_data} \n <Attached Data> \n"
        attached_request = f"\n <User Request> {user_request} \n <User Request> \n"
        plan_request = self.chain_data(attached_documentation, attached_rules, attached_data, attached_request)


        """ Establish the Objective. """
        objective_summary = self.attempt_to_establish_objective(plan_request)
        objective_request = self.chain_data(objective_summary, attached_rules, attached_request)

        """ Generate the Plan (Chain of Steps) """
        steps: List[ChainedStepModel] = self.generate_step_by_step_plan(plan_request)
        for step in steps:
            try:
                action = f"<Action> {step.step_action} <Action>"
                self.assistant_log("Reasoning Step Action:", action)
                result = self.decide_function(f"{attached_data}\n{action}\n{attached_request}")
                if result:
                    call_result = self.parse_and_call(result)

                    """ Check if Objective has been completed? """

                    if self.check_if_objective_been_completed(rAssistantReasoningPlugin.chain_data(call_result, attached_request)):
                        obj_result = self.attempt_to_complete_objective(self.chain_data(objective_request, call_result))
                        self.assistant_log("Reasoning Plan Objective Completed.", obj_result)
                        return obj_result, self.get_assistant_log_str()


                    self.assistant_log("Reasoning Step Completed.", call_result)
            except Exception as e:
                self.assistant_log("Reasoning Step ERROR:", str(e))
                continue

        """ Check if Objective has been completed? """
        obj_result = self.attempt_to_complete_objective(self.chain_data(objective_request, attached_request))
        self.assistant_log("Reasoning Plan Objective Completed.", obj_result)
        return obj_result, self.get_assistant_log_str()




class TestCaller(rAssistantPlugin):
    def greet(self, name: str, punctuation: str = "!"):
        """Return a greeting message."""
        return f"Hello, {name}{punctuation}"

    def add(self, a: int, b: int):
        """Return the sum of two numbers."""
        return a + b


# Example usage
if __name__ == "__main__":
    tool = TestCaller()

    # Get the JSON representation of the available functions
    print("Available tools:")
    print(tool.get_json_tools())

    # Example JSON input from an AI tool call to invoke the "greet" method.
    json_input = json.dumps({
        "name": "greet",
        "arguments": {"name": "Alice", "punctuation": "!!"}
    })
    print("\nCalling 'greet' with arguments from JSON input:")
    result = tool.parse_and_call(json_input)
    print("Result:", result)

    # Another example: calling the 'add' method
    json_input_add = json.dumps({
        "name": "add",
        "arguments": {"a": 5, "b": 7}
    })
    print("\nCalling 'add' with arguments from JSON input:")
    result = tool.parse_and_call(json_input_add)
    print("Result:", result)
