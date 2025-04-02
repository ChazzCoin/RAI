from abc import ABC
from typing import Optional, List, Dict, Any
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

class aiTextFormats(ABC):
    @classmethod
    def get_registry(cls): return BASE_MODELS
    @classmethod
    def format(cls, name: str): return BASE_MODELS.get(name)

# Model for Form Extraction
class FormField(BaseModel):
    label: Optional[str]
    inputType: Optional[str]

@register_format("form_extractor")
class FormExtractionModel(BaseModel):
    formTitle: Optional[str]
    fields: List[FormField]

@register_format("contact")
class RaiContactFormat(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    age: Optional[str]
    gender: Optional[str]
    occupation: Optional[str]
    position: Optional[str]
    details: Optional[str]

@register_format("contacts")
class RaiContactsFormat(BaseModel):
    holder: List[RaiContactFormat]

@register_format("create-required-data")
class fRequiredData(BaseModel):
    data: Dict[str, Any]

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

class RequiredAction(BaseModel):
    action: str
    iscomplete: bool

class RequiredActions(BaseModel):
    required_actions: List[RequiredAction]

class InteractiveElement(BaseModel):
    dom_index: int
    element: str

class InteractiveElements(BaseModel):
    interactive_elements: List[InteractiveElement]

@register_format("faq")
class ListOfQuestionAnswers(BaseModel):
    faqs: List[QuestionAnswer]

@register_format("is_event")
class IsEventModel(BaseModel):
    answer: bool

@register_format("is_true")
class IsTrueModel(BaseModel):
    answer: bool

@register_format("url")
class UrlModel(BaseModel):
    url: str
@register_format("urls")
class UrlsModel(BaseModel):
    holder: List[UrlModel]

@register_format("separate_prompt")
class SeparatePromptFormat(BaseModel):
    prompts: List[str]

@register_format("rag_query_generator")
class RagQueryGeneratorFormat(BaseModel):
    queries: List[str]

@register_format("image_table_extractor")
class ImageTableExtractorFormat(BaseModel):
    objects: List[Dict[str, Any]] = None

@register_format("herb")
class HerbFormat(BaseModel):
    name: str
    origin: Optional[str]
    description: Optional[str]
    medicinal_properties: Optional[str]
    mineral_compisition: Optional[str]
    usages: Optional[str]
    isSpiritual: Optional[bool]
    used_with: Optional[str]

@register_format("herbal")
class HerbFormat(BaseModel):
    herbs: List[HerbFormat]

@register_format("text")
class TextModel(BaseModel):
    text: str
@register_format("subject")
class SubjectModel(BaseModel):
    subject: str
@register_format("contextual_groups")
class TextsModel(BaseModel):
    groups: List[TextModel]

@register_format("step")
class StepModel(BaseModel):
    step: str
@register_format("step_by_step")
class BaseStepByStepModel(BaseModel):
    steps: List[StepModel]

@register_format("next-step")
class NextStepModel(BaseModel):
    next_step_or_action: str

class ChainedStepModel(BaseModel):
    order_index: int
    step_action: str
@register_format("chain-of-steps")
class ChainOfStepsToolFormat(BaseModel):
    chain_of_steps: List[ChainedStepModel]

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
    events: List[BaseEvent]

@register_format("location")
class BaseLocation(BaseModel):
    title: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    type: Optional[str] = None
    description: Optional[str] = None

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
class BaseLocations(BaseModel):
    holder: List[BaseLocation]

if __name__ == "__main__":

    # Fetch a specific model object by name
    model_instance = aiTextFormats.format("metadata")
    print(model_instance)
    # Example output: title='My Model Title' category='Sample Category' ...
