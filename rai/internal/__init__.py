import uuid
from typing import Dict, Any, Type, List
from pydantic import BaseModel
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools

"""
- I like the idea of having a Log built into the data model for it to give AI real-time updates about itself..
"""

class fBaseModel(BaseModel):
    id: str = str(uuid.uuid4())
    key: str = "f"
    _log: List[str] = []
    _verbose: List[str] = []

    def new(self) -> BaseModel:
        self.log("Constructing new empty model.")
        return self.model_construct()

    def model_dump(self, *args, **kwargs):
        self.log("Dumping model to json/dict")
        kwargs.setdefault('exclude', {'_log', '_verbose'})
        return super().model_dump(*args, **kwargs)

    def attempt_ai_parsing(self, text: str) -> Type[BaseModel]:
        self.log("Attempting to import text and have ai create formatted model response.")
        return rTextTools.formatter(text, self._required_data_model_type())

    def attempt_import(self, data: dict) -> BaseModel:
        self.log("Attempting to import data and create model.")
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

    def log(self, msg:str):
        formatted_msg = f"rLog: INFO: {msg}"
        print(formatted_msg)
        self._log.append(formatted_msg)
    def log_warning(self, msg:str):
        formatted_msg = f"rLog: WARNING: {msg}"
        print(formatted_msg)
        self._verbose.append(formatted_msg)
    def log_error(self, msg:str):
        formatted_msg = f"rLog: ERROR: {msg}"
        print(formatted_msg)
        self._log.append(formatted_msg)
    def log_verbose(self, msg:str):
        formatted_msg = f"rLog: VERBOSE: {msg}"
        print(formatted_msg)
        self._verbose.append(formatted_msg)

    def get_log(self): return "\n".join(self._log)

