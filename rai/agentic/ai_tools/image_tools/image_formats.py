from abc import ABC
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# Registry to store model objects
IMAGE_BASE_MODELS = {}

def register_image_format(name: str):
    def decorator(cls):
        # (Optional) Validate that cls is indeed a subclass of BaseModel
        if not issubclass(cls, BaseModel):
            raise TypeError(f"Class '{cls.__name__}' must be a subclass of BaseModel.")
        # Store the class in the registry
        IMAGE_BASE_MODELS[name] = cls
        return cls
    return decorator

class aiImageFormats(ABC):
    @classmethod
    def get_registry(cls): return IMAGE_BASE_MODELS
    @classmethod
    def format(cls, name: str): return IMAGE_BASE_MODELS.get(name)


class TableHeaderModel(BaseModel):
    header_name: Optional[str]

class TableRowAttributeModel(BaseModel):
    header_name: Optional[str]
    row_value: Optional[str]

class TableRowModel(BaseModel):
    row_count: Optional[int]
    attributes: Optional[List[TableRowAttributeModel]]

@register_image_format("table_extractor")
class TableExtractionModel(BaseModel):
    headers: List[TableHeaderModel]
    rows: List[TableRowModel]

# Model for Form Extraction
class FormField(BaseModel):
    label: Optional[str]
    inputType: Optional[str]
    required: Optional[bool]
    details: Optional[str]
# Model for Form Extraction
class FormSectionField(BaseModel):
    fields: List[FormField]
    details: Optional[str]

@register_image_format("form_extractor")
class FormExtractionModel(BaseModel):
    formTitle: Optional[str]
    sections: List[FormSectionField]
    details: Optional[str]


if __name__ == "__main__":

    # Fetch a specific model object by name
    model_instance = aiImageFormats.format("metadata")
    print(model_instance)
    # Example output: title='My Model Title' category='Sample Category' ...
