import asyncio
import inspect
import json
from typing import Callable, Dict, Any, Union, List, get_origin, get_args

from F import LIST, DICT


class mMap:
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
            return { "result": f"Failed to get signature for function {func.__name__}: {str(e)}" }

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
                    return f"Error processing list input: {e}"
            elif isinstance(json_input, str):
                try:
                    data = json.loads(json_input)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON string: {e}"
            elif isinstance(json_input, dict):
                data = json_input
            else:
                return "Input must be a JSON string, list, or dictionary."

            # Extract function name.
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            if not func_name:
                return "Missing function name ('name') in data."

            # Extract and parse arguments.
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            if args_source is None:
                return "Missing arguments ('arguments') in data."

            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return f"Error decoding 'arguments': {e}"
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return "Arguments must be a dictionary or a valid JSON string."

            if not isinstance(arguments, dict):
                return "Parsed arguments is not a dictionary."

            # Ensure the function exists and is callable.
            if not hasattr(self, func_name):
                return f"Function '{func_name}' not found."
            func = getattr(self, func_name)
            if not callable(func):
                return f"'{func_name}' is not callable."

            f"Calling function '{func_name}' with arguments: {arguments}"
            return func(**arguments)
        except Exception as e:
            return f"Error in parse_and_call: {json_input} | Exception: {e}"

    async def parse_and_call_function_async(self, json_input: Union[str, dict, list]) -> Any:
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
                    return f"Error processing list input: {e}"
            elif isinstance(json_input, str):
                try:
                    data = json.loads(json_input)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON string: {e}"
            elif isinstance(json_input, dict):
                data = json_input
            else:
                return "Input must be a JSON string, list, or dictionary."

            # Extract function name.
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            if not func_name:
                return "Missing function name ('name') in data."

            # Extract and parse arguments.
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            if args_source is None:
                return "Missing arguments ('arguments') in data."

            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return f"Error decoding 'arguments': {e}"
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return "Arguments must be a dictionary or a valid JSON string."

            if not isinstance(arguments, dict):
                return "Parsed arguments is not a dictionary."

            # Ensure the function exists and is callable.
            if not hasattr(self, func_name):
                return f"Function '{func_name}' not found."
            func = getattr(self, func_name)
            if not callable(func):
                return f"'{func_name}' is not callable."

            f"Calling function '{func_name}' with arguments: {arguments}"
            result = await func(**arguments)
            return result
        except Exception as e:
            return f"Error in parse_and_call: {json_input} | Exception: {e}"

    @staticmethod
    def map_class(cls) -> str:
        """
        Map all public callable functions of the class (excluding built-ins)
        and return a formatted string with their documentation.
        """
        if cls.__class__.__name__ in ('object', 'ABC'):
            return ""
        doc_lines = [f"Class: {cls.__class__.__name__}"]
        for name, member in cls.__class__.__dict__.items():
            if name.startswith("__"):
                continue  # Skip magic methods
            func_doc = inspect.getdoc(member) or "No documentation provided."
            doc_lines.append(f"\nFunction: {name}\nDocumentation: {func_doc}\n")
        doc_lines.append("-" * 40)
        return f"<CLASS_DOCUMENTATION>\n {' '.join(doc_lines)} \n</CLASS_DOCUMENTATION>\n"
    @staticmethod
    def get_functions_as_tools(self) -> list[dict[str, Any]]:
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
            functions.append(mMap.function_to_schema(func_obj))
        return functions
    @staticmethod
    def call_function(self, json_input: Union[str, dict, list]) -> Any:
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
                    return f"Error processing list input: {e}"
            elif isinstance(json_input, str):
                try:
                    data = json.loads(json_input)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON string: {e}"
            elif isinstance(json_input, dict):
                data = json_input
            else:
                return "Input must be a JSON string, list, or dictionary."

            # Extract function name.
            func_name = data.get('name') if isinstance(data, dict) else getattr(data, 'name', None)
            if not func_name:
                return "Missing function name ('name') in data."

            # Extract and parse arguments.
            args_source = data.get('arguments') if isinstance(data, dict) else getattr(data, 'arguments', None)
            if args_source is None:
                return "Missing arguments ('arguments') in data."

            if isinstance(args_source, str):
                try:
                    arguments = json.loads(args_source)
                except json.JSONDecodeError as e:
                    return f"Error decoding 'arguments': {e}"
            elif isinstance(args_source, dict):
                arguments = args_source
            else:
                return "Arguments must be a dictionary or a valid JSON string."

            if not isinstance(arguments, dict):
                return "Parsed arguments is not a dictionary."

            # Ensure the function exists and is callable.
            if not hasattr(self, func_name):
                return f"Function '{func_name}' not found."
            func = getattr(self, func_name)
            if not callable(func):
                return f"'{func_name}' is not callable."

            f"Calling function '{func_name}' with arguments: {arguments}"
            return func(**arguments)
        except Exception as e:
            return f"Error in parse_and_call: {json_input} | Exception: {e}"