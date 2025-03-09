import json
import inspect
from F import LIST, DICT
from rai.agentic.ai_modules import rModule

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