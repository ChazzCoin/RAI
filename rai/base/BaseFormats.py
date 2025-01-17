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


@register_format("contact")
class RaiContactFormat(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    age: Optional[str]
    gender: Optional[str]

@register_format("contacts")
class RaiContactsFormat(BaseModel):
    holder: List[RaiContactFormat]

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
    holder: List[QuestionAnswer]

@register_format("is_event")
class IsEventModel(BaseModel):
    answer: bool

@register_format("is_true")
class IsTrueModel(BaseModel):
    answer: bool

@register_format("step")
class StepModel(BaseModel):
    answer: str
@register_format("step_by_step")
class BaseEvents(BaseModel):
    holder: List[StepModel]

@register_format("event")
class BaseEvent(BaseModel):
    attendance: Optional[str] = None
    date_time: Optional[str] = None
    location: Optional[str] = None
    opponent: Optional[str] = None
    score: Optional[str] = None

    attendance_count: Optional[str] = None
    day_number: Optional[str] = None
    description: Optional[str] = None
    end_time: Optional[str] = None
    event_name: Optional[str] = None
    start_time: Optional[str] = None
    weekday: Optional[str] = None

@register_format("events")
class BaseEvents(BaseModel):
    holder: List[BaseEvent]

@register_format("location")
class BaseLocation(BaseModel):
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def full_address(self) -> Optional[str]:
        if self.address_line1 and self.city:
            parts = [
                self.address_line1,
                self.address_line2,
                self.city,
                self.state,
                self.postal_code,
                self.country,
            ]
            # Filter out any None values and join with commas
            return ", ".join(part for part in parts if part)
        return None
@register_format("locations")
class BaseLocation(BaseModel):
    holder: List[BaseLocation]

if __name__ == "__main__":

    # Fetch a specific model object by name
    model_instance = RaiBaseFormats.pipeline("metadata")
    print(model_instance)
    # Example output: title='My Model Title' category='Sample Category' ...
