from abc import ABC
from typing import Optional, List
from pydantic import BaseModel


# Registry to store model objects
BASE_MODELS = {}

def register_format(name: str):
    def decorator(cls):
        # (Optional) Validate that cls is indeed a subclass of BaseModel
        if not issubclass(cls, BaseModel):
            raise TypeError(f"Class '{cls.__name__}' must be a subclass of BaseModel.")
        # Store the class in the registry
        BASE_MODELS[name] = cls
        return cls
    return decorator

class RaiBaseFormats(ABC):
    @classmethod
    def get_registry(cls): return BASE_MODELS
    @classmethod
    def pipeline(cls, name: str): return BASE_MODELS.get(name)

@register_format("metadata")
class RaiMetadata(BaseModel):
    title: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    version: Optional[str]
    file_type: Optional[str]
    date_created: Optional[str]
    date_modified: Optional[str]
    tags: List[str]
    author: Optional[str]
    description: Optional[str]
    source: Optional[str]

@register_format("context_expander")
class RaiQueryExpander(BaseModel):
    query: Optional[str]

class TrueFalse(BaseModel):
    result: Optional[bool]
class QuestionAnswer(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
@register_format("faq")
class ListOfQuestionAnswers(BaseModel):
    results: List[QuestionAnswer]
@register_format("is_event")
class TrueOrFalse(BaseModel):
    answer: bool
@register_format("event")
class BaseEvent(BaseModel):
    # Fields from the "table" style event
    attendance: Optional[str] = None
    date_time: Optional[str] = None
    location: Optional[str] = None
    opponent: Optional[str] = None
    score: Optional[str] = None

    # Fields from the "calendar" style event
    attendance_count: Optional[str] = None
    day_number: Optional[str] = None
    description: Optional[str] = None
    end_time: Optional[str] = None
    event_name: Optional[str] = None
    start_time: Optional[str] = None
    weekday: Optional[str] = None


if __name__ == "__main__":

    # Fetch a specific model object by name
    model_instance = RaiBaseFormats.pipeline("metadata")
    print(model_instance)
    # Example output: title='My Model Title' category='Sample Category' ...
