import uuid
from typing import Dict, Any, List
from pydantic import BaseModel

"""
- I like the idea of having a Log built into the data model for it to give AI real-time updates about itself..
"""
from rai.internal.clients.redis_client import RedisDB

redis_client = RedisDB().connect()

class fBaseModel(BaseModel):
    id: str = str(uuid.uuid4())
    key: str = "f"
    _log: List[str] = []
    _verbose: List[str] = []

    """ MODEL HELPERS """
    def new(self) -> BaseModel:
        self.log_info("Constructing new empty model.")
        return self.model_construct()
    def model_dump(self, *args, **kwargs):
        self.log_info("Dumping model to json/dict")
        kwargs.setdefault('exclude', {'_log', '_verbose'})
        return super().model_dump(*args, **kwargs)
    def attempt_import(self, data: dict) -> BaseModel:
        self.log_info("Attempting to import data and create model.")
        return self.model_validate(data)
    def is_identical(self, model: BaseModel) -> bool:
        data_a = self.model_dump()
        data_b = model.model_dump()
        if data_a != data_b: return False
        return True
    def compare(self, model: BaseModel) -> Dict[str, Any]:
        diff = {}
        data_a = self.model_dump()
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
        """Generate a comprehensive documentation string for a given Pydantic model."""
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

    """ MODEL LOGGING """
    def restore_logs(self, key: str) -> list:
        try:
            logs = redis_client.redis_client.lrange(key, 0, -1)
            return [log.decode("utf-8") if isinstance(log, bytes) else log for log in logs]
        except Exception as e:
            self.log_info(f"Error loading logs for key {key}: {e}")
            return []

    def _push_log(self, key: str, message: str) -> None:
        try:
            redis_client.redis_client.rpush(key, message)
        except Exception as e:
            self.log_info(f"Error pushing log to key {key}: {e}")

    def log_info(self, msg: str) -> str:
        formatted_msg = f"fBaseModel:INFO: {msg}"
        print(formatted_msg)
        self._log.append(formatted_msg)
        self._push_log(f"model:log:{self.id}", formatted_msg)
        return formatted_msg

    def log_dump(self): return "\n".join(self._log)

    """ MODEL CACHING """
    def save_to_cache(self):
        serialized_model = self.model_dump()
        redis_client.redis_client.set(f"model:cache:{self.id}", serialized_model)

    @classmethod
    def restore_from_cache(cls, id:str):
        serialized_model = redis_client.redis_client.get(f"model:cache:{id}")
        if serialized_model:
            return cls().model_validate(serialized_model)
        return None
