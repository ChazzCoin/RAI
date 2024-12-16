from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List, Any


class VectorItem(BaseModel):
    id: str
    text: str
    vector: List[float]
    metadata: Any

class GetResult(BaseModel):
    ids: Optional[List[List[str]]]
    documents: Optional[List[List[str]]]
    metadatas: Optional[List[List[Any]]]

class SearchResult(GetResult):
    distances: Optional[List[List[float]]]

class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = "test"

class UrlForm(CollectionNameForm):
    url: str

class SearchForm(CollectionNameForm):
    query: str

class OpenAIConfigForm(BaseModel):
    url: str
    key: str
    batch_size: Optional[int] = None

""" Queries """
class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None

class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None

class ProcessDocForm(BaseModel):
    file_id: str
    collection_name: Optional[str] = None

class TextRAGForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None

class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    embedding_engine: str
    embedding_model: str

class RerankingModelUpdateForm(BaseModel):
    reranking_model: str

class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    r: Optional[float] = None
    template: Optional[str] = None
    hybrid: Optional[bool] = None

class FileConfig(BaseModel):
    max_size: Optional[int] = None
    max_count: Optional[int] = None

class ContentExtractionConfig(BaseModel):
    engine: str = ""
    tika_server_url: Optional[str] = None

class ChunkParamUpdateForm(BaseModel):
    chunk_size: int
    chunk_overlap: int

class YoutubeLoaderConfig(BaseModel):
    language: list[str]
    translation: Optional[str] = None

class WebSearchConfig(BaseModel):
    enabled: bool
    engine: Optional[str] = None
    searxng_query_url: Optional[str] = None
    google_pse_api_key: Optional[str] = None
    google_pse_engine_id: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    serpstack_api_key: Optional[str] = None
    serpstack_https: Optional[bool] = None
    serper_api_key: Optional[str] = None
    serply_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    searchapi_api_key: Optional[str] = None
    searchapi_engine: Optional[str] = None
    result_count: Optional[int] = None
    concurrent_requests: Optional[int] = None

class WebConfig(BaseModel):
    search: WebSearchConfig
    web_loader_ssl_verification: Optional[bool] = None

class ConfigUpdateForm(BaseModel):
    pdf_extract_images: Optional[bool] = None
    file: Optional[FileConfig] = None
    content_extraction: Optional[ContentExtractionConfig] = None
    chunk: Optional[ChunkParamUpdateForm] = None
    youtube: Optional[YoutubeLoaderConfig] = None
    web: Optional[WebConfig] = None
