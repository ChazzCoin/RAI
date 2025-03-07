import json
import inspect
from abc import abstractmethod
from typing import List

from F import LIST, DICT
from rai.agentic.ai_modules import rModule
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.agentic.ai_tools.text_tools.text_formats import ChainedStepModel


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

response_chain = []

class rAssistantWithChainOfStepsPlugin(rModule):

    def __init__(self): super().__init__()
    @abstractmethod
    def context(self): pass
    @classmethod
    def ask(cls, user_prompt, **kwargs):
        return cls().decide_and_call(user_prompt, **kwargs)

    @staticmethod
    def log_to_chain(data:str):
        print("Assistant Chain Log:", data)
        return response_chain.append(data)

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
        return self.get_functions_map()
    def system_prompt(self):
        return f"""
            Based on the User Prompt below, determine the best Function/Tool to select and call.
            <Function Options>
            {self.map_class()}
            </Function Options>
            {self.context()}
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
                    out = f"Error processing list input using LIST/DICT utilities. {e}"
                    self.log_to_chain(out)
                    return out
            # 2. If json_str is a str, assume it's a JSON string and parse it.
            elif isinstance(json_str, str):
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    out = f"Provided string is not valid JSON. {e}"
                    self.log_to_chain(out)
                    return out
            # 3. If already a dict, use it directly.
            elif isinstance(json_str, dict):
                data = json_str
            else:
                out = "Input must be a JSON string, list, or dictionary."
                self.log_to_chain(out)
                return out

            # Extract function name using attribute access if available, otherwise dict key.
            if hasattr(data, 'name'):
                func_name = data.name
            elif isinstance(data, dict) and 'name' in data:
                func_name = data['name']
            else:
                out = "Missing function name ('name') in the provided data."
                self.log_to_chain(out)
                return out

            # Extract arguments from the data
            if hasattr(data, 'arguments'):
                args_source = data.arguments
            elif isinstance(data, dict) and 'arguments' in data:
                args_source = data['arguments']
            else:
                out = "Missing arguments ('arguments') in the provided data."
                self.log_to_chain(out)
                return out

            # If arguments are provided as a JSON string, parse them.
            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    out = f"Error decoding the 'arguments' JSON string. {e}"
                    self.log_to_chain(out)
                    return out
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                out = "Arguments must be either a dictionary or a valid JSON string representing a dictionary."
                self.log_to_chain(out)
                return out
            # Final check: arguments must be a dict.
            if not isinstance(arguments, dict):
                out = "The parsed 'arguments' is not a dictionary."
                self.log_to_chain(out)
                return out
            # Ensure the function exists on the instance
            if not hasattr(self, func_name):
                raise AttributeError(f"Function '{func_name}' not found on the instance.")
            func = getattr(self, func_name)
            if not callable(func):
                out = f"'{func_name}' is not callable."
                self.log_to_chain(out)
                return out
            # Call the function with the provided arguments.
            self.log_to_chain(f"parse_and_call: Running function '{func_name}' with arguments: {arguments}")
            return func(**arguments)
        except Exception as e:
            # Here you might want to log the error details in a production environment.
            print(e)
            self.log_to_chain(f"parse_and_call: Error [ {e} ]")

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
    def decide_and_call(self, user_request, **kwargs):
        attached_class_documentation = self.map_class()
        attached_data = f"\n <Attached Data> {kwargs} \n <Attached Data> \n"
        attached_request = f"\n <User Request> {user_request} \n <User Request> \n"
        merged_request = f"{attached_class_documentation}\n{attached_data}\n{attached_request}\n{self.context()}"

        chain_data = {
            "user_request": attached_request,
            "attached_data": attached_data
        }

        steps: List[ChainedStepModel] = rTextTools.tool("chain-of-steps", merged_request)
        for step in steps:
            try:
                action = f"<Action> {step.step_action} <Action>"
                order = step.order_index
                result = self.decide_function(f"{attached_data}\n{action}\n{attached_request}")
                if result:
                    call_result = self.parse_and_call(result)
                    if rTextTools.tool(name="is_true",
                            user_prompt=f"{call_result}\n{attached_request}",
                            system_prompt="Do we have the information the user is requesting?",
                        ):
                        obj_result = rTextTools.tool("complete-objective", user_prompt=f"{call_result}\n{attached_request}")
                        self.log_to_chain(obj_result)
                        return obj_result, response_chain
                    self.log_to_chain(call_result)
                    chain_data[action] = call_result
                    print("Chain Assistant Functon Call Result:", call_result)
            except Exception as e:
                print("Chain Assistant Functon Call ERROR:", e)
                continue
        obj_result = rTextTools.tool("complete-objective", user_prompt=f"{chain_data}\n{attached_request}")
        self.log_to_chain(obj_result)
        return obj_result, response_chain
# Example of a child class inheriting from FunctionToolCaller

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
