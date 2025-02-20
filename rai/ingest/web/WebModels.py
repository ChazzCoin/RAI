from typing import List, Dict, Optional, Any, Tuple, Type
from pydantic import BaseModel, Field

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


class SiteExtractDetails(BaseModel):
    title: Optional[str] = None
    base_url: Optional[str] = None
    page_count: Optional[str] = None
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    urls: List[str] = Field(default_factory=list)





