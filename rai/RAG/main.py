import json
import logging
import mimetypes
import os
import shutil
import socket
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union, Tuple

import requests
import validators

from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from rai.RAG.utils import (
    get_embedding_function,
    get_model_path,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from rai.models.documents import DocumentForm, Documents
from rai.models.files import Files
from rai.config import (
    BRAVE_SEARCH_API_KEY,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONTENT_EXTRACTION_ENGINE,
    CORS_ALLOW_ORIGIN,
    DOCS_DIR,
    ENABLE_RAG_HYBRID_SEARCH,
    ENABLE_RAG_LOCAL_WEB_FETCH,
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
    ENABLE_RAG_WEB_SEARCH,
    ENV,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_ENGINE_ID,
    PDF_EXTRACT_IMAGES,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    OPENAI_API_KEY,
    OLLAMA_HOST,
    OLLAMA_PORT,
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    DEFAULT_OPENAI_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_EMBEDDING_OPENAI_BATCH_SIZE,
    RAG_FILE_MAX_COUNT,
    RAG_FILE_MAX_SIZE,
    RAG_OPENAI_API_BASE_URL,
    OPENAI_API_KEY,
    RAG_OPENAI_API_KEY,
    RAG_RELEVANCE_THRESHOLD,
    RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    DEFAULT_RAG_TEMPLATE,
    RAG_TEMPLATE,
    RAG_TOP_K,
    RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
    RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
    RAG_WEB_SEARCH_ENGINE,
    RAG_WEB_SEARCH_RESULT_COUNT,
    SEARCHAPI_API_KEY,
    SEARCHAPI_ENGINE,
    SEARXNG_QUERY_URL,
    SERPER_API_KEY,
    SERPLY_API_KEY,
    SERPSTACK_API_KEY,
    SERPSTACK_HTTPS,
    TAVILY_API_KEY,
    TIKA_SERVER_URL,
    UPLOAD_DIR,
    YOUTUBE_LOADER_LANGUAGE,
    AppConfig,
)
from rai.constants import ERROR_MESSAGES
from rai.env import SRC_LOG_LEVELS, DEVICE_TYPE, DOCKER
from rai.utils.misc import (
    calculate_sha256,
    calculate_sha256_string,
    extract_folders_after_data_docs,
    sanitize_filename,
)
from rai.utils.utils import get_admin_user, get_verified_user
from rai.RAG.connector import VECTOR_DB_CLIENT

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
    WebBaseLoader,
    YoutubeLoader,
)
from langchain_core.documents import Document

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

from rai import app
app.state.config.TOP_K = RAG_TOP_K
app.state.config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD
app.state.config.FILE_MAX_SIZE = RAG_FILE_MAX_SIZE
app.state.config.FILE_MAX_COUNT = RAG_FILE_MAX_COUNT
app.state.config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH
app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION
)
app.state.config.CONTENT_EXTRACTION_ENGINE = CONTENT_EXTRACTION_ENGINE
app.state.config.TIKA_SERVER_URL = TIKA_SERVER_URL
app.state.config.CHUNK_SIZE = CHUNK_SIZE
app.state.config.CHUNK_OVERLAP = CHUNK_OVERLAP
app.state.config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE = RAG_EMBEDDING_OPENAI_BATCH_SIZE
app.state.config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.config.RAG_TEMPLATE = RAG_TEMPLATE
app.state.config.OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.config.OPENAI_API_KEY = OPENAI_API_KEY
app.state.config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES

app.state.config.OLLAMA_HOST = OLLAMA_HOST
app.state.config.OLLAMA_PORT = OLLAMA_PORT

app.state.config.DEFAULT_OPENAI_MODEL = DEFAULT_OPENAI_MODEL
app.state.config.DEFAULT_OPENAI_EMBEDDING_MODEL = DEFAULT_OPENAI_EMBEDDING_MODEL

app.state.config.YOUTUBE_LOADER_LANGUAGE = YOUTUBE_LOADER_LANGUAGE
app.state.YOUTUBE_LOADER_TRANSLATION = None
app.state.config.ENABLE_RAG_WEB_SEARCH = ENABLE_RAG_WEB_SEARCH
app.state.config.RAG_WEB_SEARCH_ENGINE = RAG_WEB_SEARCH_ENGINE
app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = RAG_WEB_SEARCH_DOMAIN_FILTER_LIST
app.state.config.SEARXNG_QUERY_URL = SEARXNG_QUERY_URL
app.state.config.GOOGLE_PSE_API_KEY = GOOGLE_PSE_API_KEY
app.state.config.GOOGLE_PSE_ENGINE_ID = GOOGLE_PSE_ENGINE_ID
app.state.config.BRAVE_SEARCH_API_KEY = BRAVE_SEARCH_API_KEY
app.state.config.SERPSTACK_API_KEY = SERPSTACK_API_KEY
app.state.config.SERPSTACK_HTTPS = SERPSTACK_HTTPS
app.state.config.SERPER_API_KEY = SERPER_API_KEY
app.state.config.SERPLY_API_KEY = SERPLY_API_KEY
app.state.config.TAVILY_API_KEY = TAVILY_API_KEY
app.state.config.SEARCHAPI_API_KEY = SEARCHAPI_API_KEY
app.state.config.SEARCHAPI_ENGINE = SEARCHAPI_ENGINE
app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = RAG_WEB_SEARCH_RESULT_COUNT
app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = RAG_WEB_SEARCH_CONCURRENT_REQUESTS


app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.config.RAG_EMBEDDING_ENGINE,
    app.state.config.RAG_EMBEDDING_MODEL,
    app.state.sentence_transformer_ef,
    app.state.config.OPENAI_API_KEY,
    app.state.config.OPENAI_API_BASE_URL,
    app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
)

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
class ProcessDocForm(BaseModel):
    file_id: str
    collection_name: Optional[str] = None
class TextRAGForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None

async def get_status():
    return {
        "status": True,
        "chunk_size": app.state.config.CHUNK_SIZE,
        "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        "template": app.state.config.RAG_TEMPLATE,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
        "openai_batch_size": app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
    }
async def get_embedding_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "openai_config": {
            "url": app.state.config.OPENAI_API_BASE_URL,
            "key": app.state.config.OPENAI_API_KEY,
            "batch_size": app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
        },
    }
async def get_reraanking_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
    }
async def get_rag_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "file": {
            "max_size": app.state.config.FILE_MAX_SIZE,
            "max_count": app.state.config.FILE_MAX_COUNT,
        },
        "content_extraction": {
            "engine": app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "youtube": {
            "language": app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "translation": app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "searchapi_api_key": app.state.config.SEARCHAPI_API_KEY,
                "seaarchapi_engine": app.state.config.SEARCHAPI_ENGINE,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }
async def update_rag_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.pdf_extract_images
        if form_data.pdf_extract_images is not None
        else app.state.config.PDF_EXTRACT_IMAGES
    )

    if form_data.file is not None:
        app.state.config.FILE_MAX_SIZE = form_data.file.max_size
        app.state.config.FILE_MAX_COUNT = form_data.file.max_count

    if form_data.content_extraction is not None:
        log.info(f"Updating text settings: {form_data.content_extraction}")
        app.state.config.CONTENT_EXTRACTION_ENGINE = form_data.content_extraction.engine
        app.state.config.TIKA_SERVER_URL = form_data.content_extraction.tika_server_url

    if form_data.chunk is not None:
        app.state.config.CHUNK_SIZE = form_data.chunk.chunk_size
        app.state.config.CHUNK_OVERLAP = form_data.chunk.chunk_overlap

    if form_data.youtube is not None:
        app.state.config.YOUTUBE_LOADER_LANGUAGE = form_data.youtube.language
        app.state.YOUTUBE_LOADER_TRANSLATION = form_data.youtube.translation

    if form_data.web is not None:
        app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
            form_data.web.web_loader_ssl_verification
        )

        app.state.config.ENABLE_RAG_WEB_SEARCH = form_data.web.search.enabled
        app.state.config.RAG_WEB_SEARCH_ENGINE = form_data.web.search.engine
        app.state.config.SEARXNG_QUERY_URL = form_data.web.search.searxng_query_url
        app.state.config.GOOGLE_PSE_API_KEY = form_data.web.search.google_pse_api_key
        app.state.config.GOOGLE_PSE_ENGINE_ID = (
            form_data.web.search.google_pse_engine_id
        )
        app.state.config.BRAVE_SEARCH_API_KEY = (
            form_data.web.search.brave_search_api_key
        )
        app.state.config.SERPSTACK_API_KEY = form_data.web.search.serpstack_api_key
        app.state.config.SERPSTACK_HTTPS = form_data.web.search.serpstack_https
        app.state.config.SERPER_API_KEY = form_data.web.search.serper_api_key
        app.state.config.SERPLY_API_KEY = form_data.web.search.serply_api_key
        app.state.config.TAVILY_API_KEY = form_data.web.search.tavily_api_key
        app.state.config.SEARCHAPI_API_KEY = form_data.web.search.searchapi_api_key
        app.state.config.SEARCHAPI_ENGINE = form_data.web.search.searchapi_engine
        app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = form_data.web.search.result_count
        app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = (
            form_data.web.search.concurrent_requests
        )

    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "file": {
            "max_size": app.state.config.FILE_MAX_SIZE,
            "max_count": app.state.config.FILE_MAX_COUNT,
        },
        "content_extraction": {
            "engine": app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "youtube": {
            "language": app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "translation": app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "serachapi_api_key": app.state.config.SEARCHAPI_API_KEY,
                "searchapi_engine": app.state.config.SEARCHAPI_ENGINE,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }
async def get_rag_template(user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
    }
async def get_query_settings(user=Depends(get_admin_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
        "k": app.state.config.TOP_K,
        "r": app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }

def query_doc_handler(form_data: QueryDocForm):
    try:
        if app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=(
                    form_data.r if form_data.r else app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
def query_chroma(form_data: QueryCollectionsForm, hybrid=True):
    try:
        if hybrid:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=(
                    form_data.r if form_data.r else 0.0
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else 3,
            )

    except Exception as e:
        log.exception(e)
        return {}

def store_youtube_video(form_data: UrlForm, user=Depends(get_verified_user)):
    try:
        loader = YoutubeLoader.from_youtube_url(
            form_data.url,
            add_video_info=True,
            language=app.state.config.YOUTUBE_LOADER_LANGUAGE,
            translation=app.state.YOUTUBE_LOADER_TRANSLATION,
        )
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.url)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
def store_web(form_data: UrlForm, user=Depends(get_verified_user)):
    # "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm"
    try:
        loader = get_web_loader(
            form_data.url,
            verify_ssl=app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
        )
        data = loader.load()

        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.url)[:63]

        store_data_in_vector_db(data, collection_name, overwrite=True)
        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
def get_web_loader(url: Union[str, Sequence[str]], verify_ssl: bool = True):
    # Check if the URL is valid
    if not validate_url(url):
        raise ValueError(ERROR_MESSAGES.INVALID_URL)
    return SafeWebBaseLoader(
        url,
        verify_ssl=verify_ssl,
        requests_per_second=RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        continue_on_failure=True,
    )
def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            # Local web fetch is disabled, filter out any URLs that resolve to private IP addresses
            parsed_url = urllib.parse.urlparse(url)
            # Get IPv4 and IPv6 addresses
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
            # Check if any of the resolved addresses are private
            # This is technically still vulnerable to DNS rebinding attacks, as we don't control WebBaseLoader
            for ip in ipv4_addresses:
                if validators.ipv4(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
            for ip in ipv6_addresses:
                if validators.ipv6(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False
def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses

""" -> YES <- """
def store_data_in_vector_db(data, collection_name, metadata: Optional[dict] = None, overwrite: bool = False) -> tuple[bool, None]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.config.CHUNK_SIZE,
        chunk_overlap=app.state.config.CHUNK_OVERLAP,
        add_start_index=True,
    )

    docs = text_splitter.split_documents(data)

    if len(docs) > 0:
        log.info(f"store_data_in_vector_db {docs}")
        return __store_docs_in_vector_db(docs, collection_name, metadata, overwrite), None
    else:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
""" -> YES <- """
def store_text_in_vector_db(text, metadata, collection_name, overwrite: bool = False) -> bool:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.config.CHUNK_SIZE,
        chunk_overlap=app.state.config.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])
    return __store_docs_in_vector_db(docs, collection_name, overwrite=overwrite)

""" -> private - YES <- """
def __store_docs_in_vector_db(docs, collection_name, metadata: Optional[dict] = None, overwrite: bool = False) -> bool:
    log.info(f"store_docs_in_vector_db {docs} {collection_name}")

    texts = [doc.page_content for doc in docs]
    metadatas = [{**doc.metadata, **(metadata if metadata else {})} for doc in docs]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if isinstance(value, datetime):
                metadata[key] = str(value)

    try:
        if overwrite:
            if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
                log.info(f"deleting existing collection {collection_name}")
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)

        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f"collection {collection_name} already exists")
            return True
        else:
            embedding_function = get_embedding_function(
                app.state.config.RAG_EMBEDDING_ENGINE,
                app.state.config.RAG_EMBEDDING_MODEL,
                app.state.sentence_transformer_ef,
                app.state.config.OPENAI_API_KEY,
                app.state.config.OPENAI_API_BASE_URL,
                app.state.config.RAG_EMBEDDING_OPENAI_BATCH_SIZE,
            )

            VECTOR_DB_CLIENT.insert(
                collection_name=collection_name,
                items=[
                    {
                        "id": str(uuid.uuid4()),
                        "text": text,
                        "vector": embedding_function(text.replace("\n", " ")),
                        "metadata": metadatas[idx],
                    }
                    for idx, text in enumerate(texts)
                ],
            )

            return True
    except Exception as e:
        log.exception(e)
        return False


class TikaLoader:
    def __init__(self, file_path, mime_type=None):
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        if self.mime_type is not None:
            headers = {"Content-Type": self.mime_type}
        else:
            headers = {}

        endpoint = app.state.config.TIKA_SERVER_URL
        if not endpoint.endswith("/"):
            endpoint += "/"
        endpoint += "tika/text"

        r = requests.put(endpoint, data=data, headers=headers)

        if r.ok:
            raw_metadata = r.json()
            text = raw_metadata.get("X-TIKA:content", "<No text content found>")

            if "Content-Type" in raw_metadata:
                headers["Content-Type"] = raw_metadata["Content-Type"]

            log.info("Tika extracted text: %s", text)

            return [Document(page_content=text, metadata=headers)]
        else:
            raise Exception(f"Error calling Tika: {r.reason}")

""" -> YES <- """
def get_loader(filename: str, file_content_type: str, file_path: str):
    file_ext = filename.split(".")[-1].lower()
    known_type = True

    known_source_ext = [
        "go",
        "py",
        "java",
        "sh",
        "bat",
        "ps1",
        "cmd",
        "js",
        "ts",
        "css",
        "cpp",
        "hpp",
        "h",
        "c",
        "cs",
        "sql",
        "log",
        "ini",
        "pl",
        "pm",
        "r",
        "dart",
        "dockerfile",
        "env",
        "php",
        "hs",
        "hsc",
        "lua",
        "nginxconf",
        "conf",
        "m",
        "mm",
        "plsql",
        "perl",
        "rb",
        "rs",
        "db2",
        "scala",
        "bash",
        "swift",
        "vue",
        "svelte",
        "msg",
        "ex",
        "exs",
        "erl",
        "tsx",
        "jsx",
        "hs",
        "lhs",
    ]

    if (
        app.state.config.CONTENT_EXTRACTION_ENGINE == "tika"
        and app.state.config.TIKA_SERVER_URL
    ):
        if file_ext in known_source_ext or (
            file_content_type and file_content_type.find("text/") >= 0
        ):
            loader = TextLoader(file_path, autodetect_encoding=True)
        else:
            loader = TikaLoader(file_path, file_content_type)
    else:
        if file_ext == "pdf":
            loader = PyPDFLoader(
                file_path, extract_images=app.state.config.PDF_EXTRACT_IMAGES
            )
        elif file_ext == "csv":
            loader = CSVLoader(file_path)
        elif file_ext == "rst":
            loader = UnstructuredRSTLoader(file_path, mode="elements")
        elif file_ext == "xml":
            loader = UnstructuredXMLLoader(file_path)
        elif file_ext in ["htm", "html"]:
            loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
        elif file_ext == "md":
            loader = UnstructuredMarkdownLoader(file_path)
        elif file_content_type == "application/epub+zip":
            loader = UnstructuredEPubLoader(file_path)
        elif (
            file_content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or file_ext == "docx"
        ):
            loader = Docx2txtLoader(file_path)
        elif file_content_type in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ] or file_ext in ["xls", "xlsx"]:
            loader = UnstructuredExcelLoader(file_path)
        elif file_content_type in [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ] or file_ext in ["ppt", "pptx"]:
            loader = UnstructuredPowerPointLoader(file_path)
        elif file_ext == "msg":
            loader = OutlookMessageLoader(file_path)
        elif file_ext in known_source_ext or (
            file_content_type and file_content_type.find("text/") >= 0
        ):
            loader = TextLoader(file_path, autodetect_encoding=True)
        else:
            loader = TextLoader(file_path, autodetect_encoding=True)
            known_type = False

    return loader, known_type
def store_doc(collection_name: Optional[str] = Form(None), file: UploadFile = File(...)):
    # "https://www.gutenberg.org/files/1727/1727-h/1727-h.htm"

    log.info(f"file.content_type: {file.content_type}")
    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_path = f"{UPLOAD_DIR}/{filename}"

        contents = file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            f.close()

        f = open(file_path, "rb")
        if collection_name is None:
            collection_name = calculate_sha256(f)[:63]
        f.close()

        loader, known_type = get_loader(filename, file.content_type, file_path)
        data = loader.load()

        try:
            result = store_data_in_vector_db(data, collection_name)

            if result:
                return {
                    "status": True,
                    "collection_name": collection_name,
                    "filename": filename,
                    "known_type": known_type,
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            )
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )
def process_doc(form_data: ProcessDocForm):
    try:
        file = Files.get_file_by_id(form_data.file_id)
        file_path = file.meta.get("path", f"{UPLOAD_DIR}/{file.filename}")

        f = open(file_path, "rb")

        collection_name = form_data.collection_name
        if collection_name is None:
            collection_name = calculate_sha256(f)[:63]
        f.close()

        loader, known_type = get_loader(
            file.filename, file.meta.get("content_type"), file_path
        )
        data = loader.load()

        try:
            result = store_data_in_vector_db(
                data,
                collection_name,
                {
                    "file_id": form_data.file_id,
                    "name": file.meta.get("name", file.filename),
                },
            )

            if result:
                return {
                    "status": True,
                    "collection_name": collection_name,
                    "known_type": known_type,
                    "filename": file.meta.get("name", file.filename),
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            )
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )

form = TextRAGForm(
    name="",
    content="",
    collection_name="",
)
# todo
def store_text(form_data: TextRAGForm, userId:str):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)

    result = store_text_in_vector_db(
        form_data.content,
        metadata={"name": form_data.name, "created_by": userId},
        collection_name=collection_name,
    )

    if result:
        return {"status": True, "collection_name": collection_name}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


def scan_docs_dir():
    for path in Path(DOCS_DIR).rglob("./**/*"):
        try:
            if path.is_file() and not path.name.startswith("."):
                tags = extract_folders_after_data_docs(path)
                filename = path.name
                file_content_type = mimetypes.guess_type(path)

                f = open(path, "rb")
                collection_name = calculate_sha256(f)[:63]
                f.close()

                loader, known_type = get_loader(
                    filename, file_content_type[0], str(path)
                )
                data = loader.load()

                try:
                    result = store_data_in_vector_db(data, collection_name)

                    if result:
                        sanitized_filename = sanitize_filename(filename)
                        doc = Documents.get_doc_by_name(sanitized_filename)

                        if doc is None:
                            doc = Documents.insert_new_doc(
                                "user.id",
                                DocumentForm(
                                    **{
                                        "name": sanitized_filename,
                                        "title": filename,
                                        "collection_name": collection_name,
                                        "filename": filename,
                                        "content": (
                                            json.dumps(
                                                {
                                                    "tags": list(
                                                        map(
                                                            lambda name: {"name": name},
                                                            tags,
                                                        )
                                                    )
                                                }
                                            )
                                            if len(tags)
                                            else "{}"
                                        ),
                                    }
                                ),
                            )
                except Exception as e:
                    log.exception(e)
                    pass

        except Exception as e:
            log.exception(e)

    return True


def reset_vector_db(user=Depends(get_admin_user)):
    VECTOR_DB_CLIENT.reset()


def reset_upload_dir(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    try:
        # Check if the directory exists
        if os.path.exists(folder):
            # Iterate over all the files and directories in the specified directory
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"The directory {folder} does not exist")
    except Exception as e:
        print(f"Failed to process the directory {folder}. Reason: {e}")

    return True


def reset(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            log.error("Failed to delete %s. Reason: %s" % (file_path, e))

    try:
        VECTOR_DB_CLIENT.reset()
    except Exception as e:
        log.exception(e)

    return True


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling for URLs."""

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load text from the url(s) in web_path with error handling."""
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)

                # Build metadata
                metadata = {"source": path}
                if title := soup.find("title"):
                    metadata["title"] = title.get_text()
                if description := soup.find("meta", attrs={"name": "description"}):
                    metadata["description"] = description.get(
                        "content", "No description found."
                    )
                if html := soup.find("html"):
                    metadata["language"] = html.get("lang", "No language found.")

                yield Document(page_content=text, metadata=metadata)
            except Exception as e:
                # Log the error and continue with the next URL
                log.error(f"Error loading {path}: {e}")


if ENV == "dev":

    async def get_embeddings():
        return {"result": app.state.EMBEDDING_FUNCTION("hello world")}

    async def get_embeddings_text(text: str):
        return {"result": app.state.EMBEDDING_FUNCTION(text)}
