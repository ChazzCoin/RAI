import uuid
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field

from rai.base.BaseTextAgents.BaseTextFormats import BaseLocation, RaiContactFormat, BaseEvent, TextModel


class ImageData(BaseModel):
    src: str
    alt: Optional[str] = None

class ReadableContentBlock(BaseModel):
    tag: str
    text: Optional[str] = None
    images: Optional[List[ImageData]] = None
    children: Optional[List["ReadableContentBlock"]] = None

class ContentGroup(BaseModel):
    content: str
    metadata: Dict[str, Optional[str]] = {}

class WebBodyModel(BaseModel):
    headings: List[ContentGroup] = []
    paragraphs: List[ContentGroup] = []
    tables: List[ContentGroup] = []
    images: List[ContentGroup] = []
    lists: List[ContentGroup] = []
    modals: List[ContentGroup] = []
    tiles: List[ContentGroup] = []
    combined_text: Optional[str] = None

class SeleniumLocator(BaseModel):
    tag_name: str
    element_id: Optional[str] = None
    name: Optional[str] = None
    class_name: Optional[str] = None
    css_selector: Optional[str] = None

class ButtonModel(BaseModel):
    tag: str
    text: str
    id: Optional[str] = None
    css_class: List[str] = Field(default_factory=list, alias="class")
    name: Optional[str] = None
    onclick: Optional[str] = None
    attributes: Dict[str, Optional[str]] = Field(default_factory=dict)
    locator: SeleniumLocator

class JavascriptFunctionsModel(BaseModel):
    script_functions: List[str] = Field(default_factory=list)
    onclick_functions: List[str] = Field(default_factory=list)

class InputFieldModel(BaseModel):
    tag: str
    type: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    css_class: List[str] = Field(default_factory=list, alias="class")
    placeholder: Optional[str] = None
    value: Optional[str] = None
    text: Optional[str] = None       # For <textarea> contents
    options: Optional[List[str]] = None  # For <select> fields
    locator: SeleniumLocator

class LoginDetectionModel(BaseModel):
    possible_username_fields: List[InputFieldModel] = Field(default_factory=list)
    possible_password_fields: List[InputFieldModel] = Field(default_factory=list)
    possible_login_buttons: List[ButtonModel] = Field(default_factory=list)

class WebActionModel(BaseModel):
    buttons: List[ButtonModel] = Field(default_factory=list)
    javascript_functions: JavascriptFunctionsModel = Field(
        default_factory=JavascriptFunctionsModel
    )
    urls: List[str] = Field(default_factory=list)
    input_fields: List[InputFieldModel] = Field(default_factory=list)
    login_detection: LoginDetectionModel = Field(
        default_factory=LoginDetectionModel
    )

    class Config:
        allow_population_by_field_name = True


class WebLoginDetails(BaseModel):
    success: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

    # If you want to store Selenium's WebElement in the model, mark them as Any
    # and allow arbitrary types via the Config class.
    user_input: Optional[Any] = None
    pass_input: Optional[Any] = None
    login_btn: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True  # Allows storing non-JSON-serializable objects

class TextLineClassification(BaseModel):
    header: bool = False
    footer: bool = False
    chapter: bool = False

class TextLineDetail(BaseModel):
    text: str
    classification: TextLineClassification

class SiteExtractDetails(BaseModel):
    title: Optional[str] = None
    base_url: Optional[str] = None
    page_count: Optional[str] = None
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    urls: List[str] = Field(default_factory=list)


class BasePageModel(BaseModel):
    id: Optional[str] = str(uuid.uuid4())
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    file_name: Optional[str] = None
    page_count: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NLPAssistantModel(BaseModel):
    tokens: List[str] = Field(default_factory=list)
    bigrams: List[str] = Field(default_factory=list)
    sentences: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    pos_tags: List[Tuple[str, str]] = Field(default_factory=list)
    named_entities: List[Tuple[str, str]] = Field(default_factory=list)
    lemmas: List[str] = Field(default_factory=list)
    dependency_parse: List[Tuple[str, str, str]] = Field(default_factory=list)
    frequency_distribution: Dict[str, int] = Field(default_factory=dict)
    urls: List[str] = Field(default_factory=list)
    sentiment: Dict[str, float] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)

class FNLPAssistantModel(BaseModel):
    sentences: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    addresses: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    lines: List[TextLineDetail] = Field(default_factory=list)

    top_words: Optional[List[str]] = None
    words: Optional[List[str]] = None
    bi_words: Optional[List[str]] = None
    tri_words: Optional[List[str]] = None
    quad_words: Optional[List[str]] = None

    character_count: Optional[int] = None
    word_count: Optional[int] = None
    sentence_count: Optional[int] = None
    paragraph_count: Optional[int] = None

class TextNLPAgentModel(BaseModel):
    summary: Optional[str] = None
    sentiment: Optional[List[str]] = None
    queries: Optional[List[str]] = None
    paraphrase: Optional[str] = None
    document_type: Optional[List[str]] = None
    context_groups: List[TextModel] = Field(default_factory=list)

class TextImageModel(BaseModel):
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None
    tables: List[Dict[str, Any]] = Field(default_factory=list)


class PageAnalysisModel(BaseModel):

    details: BasePageModel = Field(default_factory=BasePageModel)

    content: Optional[str] = None
    content_extended: Optional[str] = None
    sub_content: Optional[List[str]] = None

    nlp: Optional[NLPAssistantModel] = None
    fnlp: Optional[FNLPAssistantModel] = None
    nlp_agent: Optional[TextNLPAgentModel] = None
    images: Optional[List[ImageData]] = None

    contacts: List[RaiContactFormat] = Field(default_factory=list)
    locations: List[BaseLocation] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[BaseEvent] = Field(default_factory=list)

class DocumentAnalysisModel(BaseModel):

    details: BasePageModel = Field(default_factory=BasePageModel)
    pages: Optional[List[PageAnalysisModel]] = None


