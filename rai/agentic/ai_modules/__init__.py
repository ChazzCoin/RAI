import inspect
import json
from abc import abstractmethod
from typing import Any, get_origin, Union, get_args, List, Dict, Callable

from F import DICT, LIST

from rai.agentic.ai_assistants.QCache import VectorCache
from rai.agentic.ai_assistants.QStore import VectorStore
from rai.assistant.connectors import rAI

rAI = rAI('openai')
rStore = VectorStore()
rCache = VectorCache()

ASSISTANT_LOG_CHAIN = []


class rAssistantLogModule:

    @classmethod
    def assistant_log(cls, *data: str) -> str:
        """Log messages to the assistant log chain."""
        for line in data:
            info_message = f"r{cls.__name__}: INFO: " + line
            print(info_message)
            ASSISTANT_LOG_CHAIN.append(info_message)
        return str(data)

    @classmethod
    def assistant_error_log(cls, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix."""
        for line in data:
            error_message = f"r{cls.__name__}: ERROR: " + line
            print(error_message)
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

class rModule:

    @staticmethod
    @abstractmethod
    def module_name() -> str: pass

    @staticmethod
    def tag_data(tag:str, data:str): return f"<{str(tag).capitalize()}>\n {data} \n</{str(tag).capitalize()}"

    @staticmethod
    def chain_data(*args: Any) -> str:
        """
        Join provided arguments into a single string. Non-string types are converted to strings.
        """
        return "\n".join(str(arg) for arg in args)

    @staticmethod
    def r_engine() -> str: return rAI.CURRENT_ENGINE
    @staticmethod
    def r_switch_engine(engine:str): return rAI.switch_engine(engine)
    @staticmethod
    def rAI() -> rAI: return rAI
    @staticmethod
    def rStore() -> VectorStore: return rStore
    @staticmethod
    def rCache() -> VectorCache: return rCache
    @staticmethod
    def rRedis(): return rCache.redis_client


class rMapper:
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



class rErrorHandler(rMapper, rAssistantLogModule):

    error_data = None

    def error_handler_decision_prompt(self) -> str:
        return """
            Based on the following Error Message and Assistant Process Log, which function should be called to best handle the error?
        """

    def decide_function(self, error: str) -> Any:
        """Generate a decision on which function/tool to call based on the user prompt."""
        try:
            tools = self.get_external_json_tools()
            self.assistant_log("Attempting to decide on a function.")
            decision = rAI.generate_function(
                user=f"\n<ASSISTANT_LOG>\n{self.get_assistant_log_str()}\n</ASSISTANT_LOG>\n<ERROR>\n{error}\n</ERROR>\n",
                system=self.error_handler_decision_prompt(),
                functions=tools,
                raw_result=True
            )
            self.assistant_log(f"Decision made: [ {decision} ]")
            return decision
        except Exception as e:
            self.assistant_log(f"Error in deciding function: [ {str(e)} ]")
            return None

    def handle_error(self, error:str):
        result = self.decide_function(error)
        call_result = self.parse_and_call_function(result)
        self.error_data = call_result
        self.assistant_log(f"Error Handler Call Result: [ {call_result} ]")
        return call_result