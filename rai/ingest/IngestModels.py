
import uuid
from typing import List, Dict, Optional, Any, Tuple, Type

from crawl4ai import CrawlResult
from pydantic import BaseModel, Field

from rai.ingest.web.WebModels import ImageData
from rai.raigents.base.BaseTextAgents.BaseTextFormats import TextModel, RaiContactFormat, BaseLocation, BaseEvent


class TextLineClassification(BaseModel):
    header: bool = False
    footer: bool = False
    chapter: bool = False

class TextLineDetail(BaseModel):
    text: str
    classification: TextLineClassification

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

class TextMediaModel(BaseModel):
    bytes: Optional[bytes] = None
    source: Optional[str] = None
    type: Optional[str] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None
    screenshot: Optional[str] = None


class IngestBrief(BaseModel):
    id: Optional[str] = str(uuid.uuid4())

    success: bool = False

    index: int = 0
    source: str = ""
    original_content: str = ""
    content: str = ""

    metadata: Optional[Dict[str, Any]] = None

    images: Optional[List[ImageData]] = None
    pdfs: List[Any] = Field(default_factory=list)
    docxs: List[Any] = Field(default_factory=list)
    pptxs: List[Any] = Field(default_factory=list)
    excels: List[Any] = Field(default_factory=list)
    csvs: List[Any] = Field(default_factory=list)
    jsons: List[Any] = Field(default_factory=list)
    jsonls: List[Any] = Field(default_factory=list)

    page_screenshot: Optional[Any] = None
    page_pdf: Optional[Any] = None
    crawl_result: Type[CrawlResult] = None

class IngestPage(BaseModel):
    id: Optional[str] = str(uuid.uuid4())
    details: BasePageModel = Field(default_factory=BasePageModel)

    brief: Optional[IngestBrief] = None

    content: Optional[str] = None
    content_extended: Optional[str] = None
    agent_content: Optional[str] = None
    embedded_content: Optional[Any] = None
    sub_content: Optional[List[str]] = None

    nlp: Optional[NLPAssistantModel] = None
    fnlp: Optional[FNLPAssistantModel] = None
    nlp_agent: Optional[TextNLPAgentModel] = None
    images: Optional[List[ImageData]] = None

    contacts: List[RaiContactFormat] = Field(default_factory=list)
    locations: List[BaseLocation] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[BaseEvent] = Field(default_factory=list)


class IngestRecord(BaseModel):
    id: Optional[str] = str(uuid.uuid4())
    details: BasePageModel = Field(default_factory=BasePageModel)
    pages: Optional[List[IngestPage]] = None
