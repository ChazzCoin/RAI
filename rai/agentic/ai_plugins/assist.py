import json
import inspect
from abc import abstractmethod
from typing import Any, Type, List

from F import LIST, DICT
from pydantic import BaseModel

from rai.agentic.ai_modules import rModule
from rai.ingest.utilities.TextUtils import TextProcessor

ASSIST_LOG = []

class rAssistantPlugin(rModule):

    initial_request_tagged = f"<USER REQUEST> </USER REQUEST>"

    class AssistResponse(BaseModel):
        answer: str
        data: Any

    data = None

    @staticmethod
    def module_name() -> str: pass

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
    def assistant_log(cls, *data: str) -> str:
        """Log messages to the assistant log chain."""
        for line in data:
            info_message = "INFO: " + line
            print(f"r{cls.module_name()}", info_message)
            ASSIST_LOG.append(info_message)
        return str(data)

    @classmethod
    def assistant_error_log(cls, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix."""
        for line in data:
            error_message = "ERROR: " + line
            print(f"r{cls.module_name()}", error_message)
            ASSIST_LOG.append(error_message)
        return str(data)

    @staticmethod
    def get_assistant_log() -> List[str]:
        """Retrieve the assistant log as a list of strings."""
        return ASSIST_LOG

    @staticmethod
    def get_assistant_log_str() -> str:
        """Retrieve the assistant log as a single string."""
        return str(ASSIST_LOG)

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
        self.assistant_log(f"Decision Made: {str(decision) or 'Unable to parse decision for assistant log.'}")
        return decision
    def generate_final_response(self) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            self.assistant_log("Generating final response for user.")
            final_response_request = self.chain_data(
                self.get_assistant_log_str(),
                self.initial_request_tagged,
            )
            response = self.rAI().generate(
                user=final_response_request,
                system="You are a personal assistant, analyze the data provided, create the appropriate summarized response of what happen to send back to the user."
            )
            self.assistant_log("Final Response Generated", response)
            return response
        except Exception as e:
            return self.assistant_error_log(f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>")

    def decide_and_call(self, user_prompt, **kwargs):
        self.initial_request_tagged = f"\n<User Prompt>\n {user_prompt} \n {kwargs} \n<User Prompt>\n"
        self.assistant_log(f"Initial Request: {self.initial_request_tagged}")
        result = self.decide_function(self.initial_request_tagged)
        call_result = self.parse_and_call(result)
        for_log = TextProcessor.ensure_within_limit(str(call_result) or 'No Result', limit=1000)
        self.assistant_log(f"Function Call Result: {for_log}")
        if call_result:
            self.data = call_result
        self.assistant_log("Generating and Returning Final Response for the User.")
        final_response = self.generate_final_response()
        return rAssistantPlugin.AssistResponse(
            answer=final_response,
            data=self.data,
        )