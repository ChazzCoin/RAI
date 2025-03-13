import inspect
import json
from abc import abstractmethod
from typing import Any, get_origin, Union, get_args, List, Dict, Callable, Type, TypeVar, Optional, Generic

from F import DICT, LIST
from pydantic import BaseModel, Field, create_model

from rai.agentic.ai_assistants.QCache import VectorCache
from rai.agentic.ai_assistants.QStore import VectorStore
from rai.agentic.ai_tools.image_tools.r_tools import rImageTools
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI

rAI = rAI('openai')
rStore = VectorStore()
rCache = VectorCache()

ASSISTANT_LOG_CHAIN = []


class mAssistLog:

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

    class AssistResponse(BaseModel):
        prefix: str
        session_id: str
        answer: str
        data: Any

    @staticmethod
    @abstractmethod
    def module_name() -> str: pass

    @staticmethod
    @abstractmethod
    def _required_model() -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        pass

    @staticmethod
    def tag_data(tag:str, data:str): return f"<{str(tag).capitalize()}>\n {data} \n</{str(tag).capitalize()}"

    @staticmethod
    def chain_data(*args: Any) -> str:
        """
        Join provided arguments into a single string. Non-string types are converted to strings.
        """
        return "\n".join(str(arg) for arg in args)

    def ask_ai_to_parse_text_to_required_model(self, text: str) -> Type[BaseModel]:
        return rTextTools.formatter(text, self._required_model())

    @staticmethod
    def r_text_tools() -> Type[rTextTools]: return rTextTools
    @staticmethod
    def r_image_tools() -> Type[rImageTools]: return rImageTools
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
"""

Example Data:
'StoreDocument'
    id
    document
    metadata 
    distance
    
'fEmail'
    id: Optional[str] = None
    sender: EmailStr
    recipients: List[EmailStr]
    subject: str
    body: str
    is_html: bool = False
    date: Optional[datetime.datetime] = None

"""
DATA_LOG: List[str] = []

class mData:

    _data_refresh_count: int = 0
    _temp_data: [BaseModel] = []
    _data: [BaseModel] = []
    _archived_data: Dict[int, List[BaseModel]] = {}

    @property
    def data_docs(self): return mMap.map_class(mData)

    @property
    def data_tools(self): return mMap.get_functions_as_tools(mData)

    def data_log(self, msg:str):
        formatted_msg = f"mDataModule: {self._required_data_model_type_name()}: {msg}"
        print(formatted_msg)
        DATA_LOG.append(formatted_msg)

    @staticmethod
    def data_log_str(): "\n".join(DATA_LOG)

    @staticmethod
    def create_new_model_type(name: str, **fields) -> Type[BaseModel]:
        return create_model(name, **fields)

    @staticmethod
    @abstractmethod
    def _required_data_model_type() -> BaseModel:
        """Return the required data model for the assistant."""
        pass

    def _required_data_model_type_name(self) -> str:
        """Return the required data model for the assistant."""
        return self._required_data_model_type().__class__.__name__

    def ask_ai_to_create_data_model(self, text: str) -> Type[BaseModel]:
        return rTextTools.formatter(text, self._required_data_model_type())

    def _new_data_instance(self) -> BaseModel:
        return self._required_data_model_type().model_construct()

    def get_data(self) -> List[BaseModel]: return self._data
    def get_data_archived(self) -> Dict[int, List[BaseModel]]: return self._archived_data

    def has_data(self) -> bool:
        if not self._data: return False
        if len(self._data) == 0: return False
        return True

    def _move_data_to_archive(self):
        self.data_log("Moving current data to archive.")
        self._archived_data[self._data_refresh_count] = self._data
        self._data_refresh_count += 1

    def attempt_quick_parse_or_empty_model(self, data: Any) -> BaseModel:
        required_model: BaseModel = self._required_data_model_type().model_construct()  # abstract method to get the model type
        try:
            required_model = required_model.model_copy(update=data)
            self.data_log("Quick Parse Successful. Data Object Created.")
            return required_model
        except Exception as e:
            self.data_log(f"Quick Parse Failed. [ {str(e)} ]")
            return required_model

    def import_new_data(self, request_or_datas: Any, **additional_data) -> List[Any]:
        if not request_or_datas or request_or_datas is None: return []
        self._temp_data = []
        self.data_log("Attempting to Import Data.")
        if type(request_or_datas) in [list, tuple]:
            self.data_log("Data IN is a list/tuple.")
            for item in request_or_datas:
                temp = self.__handle_single_item(item, **additional_data)
                self._temp_data.append(temp)
        else:
            self.data_log("Data IN is a single object.")
            item = self.__handle_single_item(request_or_datas, **additional_data)
            self._temp_data.append(item)

        if self.has_data():
            self._move_data_to_archive()
        self._data = self._temp_data
        if self.has_data():
            self.data_log("Data Import Successful.")
        return self._data

    def __handle_single_item(self, request_or_data: Any, **additional_data) -> Optional[BaseModel]:
        """
        Robustly extract and merge data into the required model type.

        Workflow:
          1. Process `request_or_data`:
             - If it is an instance of the required model or a dictionary, update/merge it.
             - If it is a list or tuple, recursively search for valid model data.
             - Otherwise, treat it as text (converting to string if needed).
          2. Process `additional_data` similarly:
             - If any additional data directly matches the model or is found nested in lists/tuples, update immediately.
             - Otherwise, collect key/value pairs to append to the text prompt.
          3. Fall back on the text-parsing method (auto_format_text_to_data_model) as a last resort.

        Returns:
          An updated instance of the required model type, or None if extraction fails.
        """
        required_model: BaseModel = self._required_data_model_type().model_construct()  # abstract method to get the model type
        try:
            required_model = required_model.model_copy(update=request_or_data)
            return required_model
        except Exception as e:
            self.data_log(str(e))

        additional_strs = []  # To collect simple key/value pairs for context

        def try_simple_update(item: Any) -> Optional[BaseModel]:
            if not item: return None
            if isinstance(item, self._required_data_model_type()): return self.create_data_model(item.model_dump())
            if isinstance(item, dict): return self.create_data_model(item)
            return None

        def deep_search_list(items: Any, depth: int = 0) -> Optional[BaseModel]:
            if not items or depth >= 100: return None
            for element in items:
                result = try_simple_update(element)
                if result:
                    return result
                if isinstance(element, (list, tuple)):
                    nested_result = deep_search_list(element, depth + 1)
                    if nested_result:
                        return nested_result
            return None

        def parse_text(text: str) -> Optional[BaseModel]:
            if not text: return None
            result = self.ask_ai_to_create_data_model(text=text)
            return try_simple_update(result)

        # --- Process the primary input (request_or_data) ---
        # First, try to directly update using request_or_data.
        result = try_simple_update(request_or_data)
        if result:
            return result

        # If request_or_data is a list/tuple, recursively search for valid model data.
        if isinstance(request_or_data, (list, tuple)):
            result = deep_search_list(request_or_data)
            if result:
                return result

        # If request_or_data isn't already valid data, convert it to text.
        if request_or_data is not None:
            req_text = request_or_data if isinstance(request_or_data, str) else str(request_or_data)
        else:
            req_text = "No User/Request Prompt Provided."

        # --- Process any additional data provided ---
        for key, value in additional_data.items():
            result = try_simple_update(value)
            if result:
                return result
            elif isinstance(value, (list, tuple)):
                result = deep_search_list(value)
                if result:
                    return result
            elif isinstance(value, (str, int, float, bool)):
                additional_strs.append(f"{key}={value}")

        # Append any simple additional data as extra context to the request text.
        if additional_strs:
            additional_text = "\n".join(additional_strs)
            req_text = f"{req_text}\n{additional_text}"

        # --- Fall back on text parsing ---
        return parse_text(req_text)

    def update_data(self, obj: BaseModel, updates: Dict[str, Any]) -> BaseModel:
        """
        - Update an existing Pydantic model instance with new data.
        Leverages the built-in .copy() method with the `update` parameter to return a new instance.
        """
        try:
            return obj.model_copy(update=updates)
        except Exception as e:
            self.data_log(str(e))
            return self.create_data_model(updates)
    def create_data_model(self, data: Dict[str, Any]) -> BaseModel:
        """
        - Validates arbitrary data against a given Pydantic model.
        Returns a valid model instance if the data passes validation, otherwise raises a ValidationError.
        """
        return self._new_data_instance().model_validate(data)
    def deep_update_model(self, obj: BaseModel, updates: Dict[str, Any]) -> BaseModel:
        """
        - Recursively update a Pydantic model instance.
        Particularly useful for models with nested sub-models. For each key in the updates,
        if the corresponding value in the original instance is a dict and the update is also a dict,
        the update is merged recursively.
        """
        # Start with a dictionary representation of the instance
        data = obj.model_dump()
        for key, value in updates.items():
            if key in data and isinstance(data[key], dict) and isinstance(value, dict):
                data[key].update(value)
            else:
                data[key] = value
        obj = self.create_data_model(data)
        return obj
    def model_diff(self, obj: BaseModel, model: BaseModel) -> Dict[str, Any]:
        """
        - Compute a difference between two Pydantic model instances.
        Returns a dictionary where each key corresponds to a field with differing values,
        and the value is another dict containing the values from each instance.
        """
        diff = {}
        data_a = obj.model_dump()
        data_b = model.model_dump()
        all_keys = set(data_a.keys()).union(data_b.keys())
        for key in all_keys:
            if data_a.get(key) != data_b.get(key):
                diff[key] = {"data": data_a.get(key), "model": data_b.get(key)}
        return diff
    def get_field_metadata(self) -> Dict[str, Any]:
        """
        - Extract metadata for each field in the given Pydantic model.
        Useful for introspection, generating dynamic forms, or API documentation.
        Returns a dictionary mapping each field name to its type, default value, requirement status, and alias.
        """
        metadata = {}
        for name, field in self._required_data_model_type().model_fields.__dict__.items():
            metadata[name] = {
                "type": field.type_,
                "default": field.default,
                "required": field.required,
                "alias": field.alias
            }
        return metadata
    def document_model(self) -> str:
        """
        Generate a comprehensive documentation string for a given Pydantic model.

        This documentation includes:
          - Model name and its description (if provided via the class docstring).
          - A complete breakdown of each field, including:
              * Field name.
              * Type.
              * Required flag.
              * Default value or indication of a default factory.
              * Alias (if different from the field name).
              * Additional metadata (e.g., title, description, examples, or any extra parameters from Field).

        Returns:
            str: A detailed documentation string of the model.

        Example Output:

            Model Documentation: User
            =========================
            Description:
            A user model representing an individual in the system.

            Fields:
            -------
            Field: id
              Type: <class 'int'>
              Required: True
              Default: <required>

            Field: name
              Type: <class 'str'>
              Required: False
              Default: 'Anonymous'
              Additional Info:
                - Title: User Name
                - Description: The full name of the user.
        """
        doc_lines = []
        model = self._required_data_model_type()
        # Header section with the model name
        header = f"Model Documentation: {model.__name__}"
        doc_lines.append(header)
        doc_lines.append("=" * len(header))
        doc_lines.append("")

        # Include model docstring if available
        model_doc = model.__doc__.strip() if model.__doc__ else "No description provided."
        doc_lines.append("Description:")
        doc_lines.append(model_doc)
        doc_lines.append("")

        # Section for fields metadata
        doc_lines.append("Fields:")
        doc_lines.append("-------")
        for field_name, field in model.model_fields.__dict__.items():
            doc_lines.append(f"Field: {field_name}")
            doc_lines.append(f"  Type: {field.outer_type_}")
            doc_lines.append(f"  Required: {field.required}")

            # Handle default values and default factories.
            if field.default_factory is not None:
                doc_lines.append("  Default Factory: Present")
            elif field.default is not None:
                doc_lines.append(f"  Default: {field.default!r}")
            else:
                # If no default and required, mark as required
                doc_lines.append("  Default: <required>" if field.required else "  Default: None")

            # Only output alias if it's different from the field name.
            if field.alias != field_name:
                doc_lines.append(f"  Alias: {field.alias}")

            # Gather additional Field metadata if available.
            additional_info = []
            if field.field_info.title:
                additional_info.append(f"Title: {field.field_info.title}")
            if field.field_info.description:
                additional_info.append(f"Description: {field.field_info.description}")
            if field.field_info.extra:
                for k, v in field.field_info.extra.items():
                    additional_info.append(f"{k}: {v}")
            if additional_info:
                doc_lines.append("  Additional Info:")
                for info in additional_info:
                    doc_lines.append(f"    - {info}")
            doc_lines.append("")  # Blank line between fields

        return "\n".join(doc_lines)


