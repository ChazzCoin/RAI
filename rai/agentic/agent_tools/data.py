import json
from typing import Dict, Any, Optional, List, Type, TypeVar
from pydantic import BaseModel, create_model
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.ai_modules.log import mLog
from rai.assistant.connectors import LLM

T = TypeVar("T", bound=BaseModel)


def inject_generic(model: T) -> str:
    def safe(value):
        return value if value not in (None, "") else "no data found"
    if not model: return "No Data"
    return "\n".join(f"{key}: {safe(value)}" for key, value in model.model_dump().items())

class ToolData(mLog):

    session_id: str = "system"

    _data_refresh_count: int = 0
    _temp_data: [BaseModel] = []
    _data: [BaseModel] = []
    _archived_data: Dict[int, List[BaseModel]] = {}

    def cache_key(self): return f"cache:data:{self.session_id}"
    def cache_archive_key(self): return f"cache:data:archive:{self.session_id}"
    def cache_refresh_key(self): return f"cache:data:refresh:{self.session_id}"

    @staticmethod
    def create_new_model_type(name: str, **fields) -> Type[BaseModel]:
        return create_model(name, **fields)

    @staticmethod
    def _required_data_model_type() -> Type[ToolResult]:
        """Return the required data model for the assistant."""
        return ToolResult

    def _required_data_model_type_name(self) -> str:
        """Return the required data model for the assistant."""
        return self._required_data_model_type().__class__.__name__

    def ask_ai_to_create_data_model(self, text: str) -> Type[BaseModel]:
        return LLM.formatter(text, self._required_data_model_type())

    def _new_data_instance(self) -> BaseModel:
        return self._required_data_model_type().model_construct()

    def inject_latest_import(self) -> str:
        data = self.get_data()
        if not data or len(data) == 0: return "NO DATA FOUND"
        summary = ""
        if type(data) in [list, tuple]:
            for item in data:
                if type(item) == ToolResult:
                    summary += ToolResult.inject(item)
                else:
                    summary += inject_generic(item)
        else:
            if type(data) == ToolResult:
                summary += ToolResult.inject(data)
            else:
                summary += inject_generic(data)
        result = f"""
            <LATEST_DATA_RESULTS>
            {summary}
            </LATEST_DATA_RESULTS>
        """
        print(result)
        return result

    def get_data(self) -> List[BaseModel]: return self._data

    def get_last_item_in_data(self) -> Optional[BaseModel]:
        if not self.has_data(): return None
        return self._data[-1]

    def get_data_archived(self) -> Dict[int, List[BaseModel]]: return self._archived_data
    def has_data(self) -> bool:
        if not self._data: return False
        if len(self._data) == 0: return False
        return True
    def _move_data_to_archive(self):
        self._archived_data[self._data_refresh_count] = self._data
        self._data_refresh_count += 1
        self.log_data(f"Moved previous imported data to archive with [ {self._data_refresh_count} ] currently archived data imports.")
    def attempt_quick_parse_or_empty_model(self, data: Any) -> BaseModel:
        required_model: BaseModel = self._required_data_model_type().model_construct()  # abstract method to get the model type
        try:
            required_model = required_model.model_copy(update=data)
            self.log_data("Quick Parse Successful. Data Object Created.")
            return required_model
        except Exception as e:
            self.log_data(f"Quick Parse Failed. [ {str(e)} ]")
            return required_model

    def find_data_by_id(self, id) -> Optional[BaseModel]:
        for item in self._data:
            if item.id == id:
                return item
        return None

    """ CACHING """
    def restore_data(self, session_id:str=None):
        if session_id: self.session_id = session_id
        self._load_data_cache()
        self._load_archived_data_cache()
        self._load_data_refresh_count()

    def _save_data_cache(self) -> None:
        try:
            data_dicts = [item.model_dump() for item in self._data]
            self.redis_client.set(self.cache_key(), json.dumps(data_dicts))
        except Exception as e:
            self.log_error(f"Error saving _data: {str(e)}")
    def _load_data_cache(self) -> None:
        try:
            cached = self.redis_client.get(self.cache_key())
            if cached:
                data_list = json.loads(cached)
                self._data = [self._required_data_model_type().model_validate(item) for item in data_list]
            else:
                self._data = []
        except Exception as e:
            self.log_error(f"Error loading _data: {str(e)}")
            self._data = []
    def _save_archived_data_cache(self) -> None:
        try:
            archived_serialized = {
                str(key): [model.model_dump() for model in models]
                for key, models in self._archived_data.items()
            }
            self.redis_client.set(f"{self.cache_archive_key()}", json.dumps(archived_serialized))
        except Exception as e:
            self.log_error(f"Error saving _archived_data: {str(e)}")
    def _load_archived_data_cache(self) -> None:
        try:
            cached = self.redis_client.get(f"{self.cache_archive_key()}")
            if cached:
                archived_serialized = json.loads(cached)
                self._archived_data = {
                    int(key): [self._required_data_model_type().model_validate(item) for item in models]
                    for key, models in archived_serialized.items()
                }
            else:
                self._archived_data = {}
        except Exception as e:
            self.log_error(f"Error loading _archived_data: {str(e)}")
            self._archived_data = {}
    def _save_data_refresh_count(self) -> None:
        try: self.redis_client.set(self.cache_refresh_key(), self._data_refresh_count)
        except Exception as e: self.log_error(f"Error saving _data_refresh_count: {str(e)}")
    def _load_data_refresh_count(self) -> None:
        try:
            cached = self.redis_client.get(self.cache_refresh_key())
            if cached: self._data_refresh_count = int(cached)
            else: self._data_refresh_count = 0
        except Exception as e:
            self.log_error(f"Error loading _data_refresh_count: {str(e)}")
            self._data_refresh_count = 0

    """ DATA REPORT """
    def report_data_count(self) -> int:
        return len(self._data) or 0
    def report_prompt(self) -> str:
        return f"""
            <DATA_ASSISTANT_PROCESS_LOG>
                {self.get_log_str("data")}
            </DATA_ASSISTANT_PROCESS_LOG>
            - HAS DATA CURRENTLY LOADED: [ {self.has_data()} ]
            - CURRENT ITEMS IN DATA LIST: [ {self.report_data_count()} ]
        """
    def generate_data_report(self):
        return LLM.tool(
            name="generate",
            user_prompt=self.report_prompt(),
            system_prompt=""
        )

    """ IMPORTING """
    def import_new_data(self, request_or_datas: Any, **additional_data) -> List[Any]:
        if not request_or_datas or request_or_datas is None: return []
        self._temp_data = []
        self.log_data("Attempting to Import New Data.")
        if type(request_or_datas) in [list, tuple]:
            self.log_data("Data IN is a list/tuple.")
            for item in request_or_datas:
                temp = self.__handle_single_item(item, **additional_data)
                self._temp_data.append(temp)
        else:
            self.log_data("Data IN is a single object.")
            item = self.__handle_single_item(request_or_datas, **additional_data)
            self._temp_data.append(item)
        if self.has_data():
            self._move_data_to_archive()
        self._data = self._temp_data
        if self.has_data():
            self.log_data("Data Import Successful.")
            self.log_data(f"Data Assistant is holding [ {len(self.get_data())} ] items.")
        else:
            self.log_data("Data Import Failed.")
            self.log_data(f"Data Assistant is holding [ {len(self.get_data())} ] items.")
            self.log_data(f"Data Model Scheme and Breakdown\n{self.document_model()}")

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
            self.log_verbose(f"Parsing attempt failed. Moving on to next attempt. {str(e)}")

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
            self.log_verbose("Attempting to update")
            return obj.model_copy(update=updates)
        except Exception as e:
            self.log_verbose(str(e))
            return self.create_data_model(updates)
    def create_data_model(self, data: Dict[str, Any]) -> BaseModel:
        """
        - Validates arbitrary data against a given Pydantic model.
        Returns a valid model instance if the data passes validation, otherwise raises a ValidationError.
        """
        self.log_verbose("Creating New Data Model Object")
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
