import json
import logging
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np
import requests
from pydantic import BaseModel
from assistant.ollama_client import generate_chroma_embeddings
from rai.RAG.utils import query_collection_with_hybrid_search, query_collection
from rai.files import RaiPath
from rai.models.documents import DocumentForm, Documents
from rai.constants import ERROR_MESSAGES
from rai.env import SRC_LOG_LEVELS
from rai.utils.misc import (
    calculate_sha256,
    calculate_sha256_string,
    extract_folders_after_data_docs,
    sanitize_filename,
)
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
)
from langchain_core.documents import Document
from rai import app

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

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
def __validate_and_fix_embeddings(items):
    """
    Validates and fixes embeddings. If an embedding contains nested lists/arrays or
    non-float32 values, it is flattened and converted to a list of float32 values.

    Args:
    - items (list): List of dictionaries containing 'id', 'text', 'vector', and 'metadata'.

    Returns:
    - fixed_items (list): The same list of items with all embeddings in the correct format.
    """

    def flatten_embedding(embedding):
        """Recursively flattens any nested lists or arrays into a single list of floats."""
        if isinstance(embedding, (list, np.ndarray)):
            return [item for sublist in embedding for item in flatten_embedding(sublist)]
        else:
            return [embedding]

    fixed_items = []

    for item in items:
        embedding = item['vector']

        # Ensure the embedding is a NumPy ndarray or list
        if isinstance(embedding, np.ndarray):
            # Check if the embedding is 1-dimensional or needs flattening
            if embedding.ndim > 1:
                embedding = flatten_embedding(embedding)
            else:
                embedding = embedding.tolist()

        # If the embedding is a list, flatten it if necessary
        elif isinstance(embedding, list):
            embedding = flatten_embedding(embedding)

        # Ensure all values are of type float32
        embedding = [np.float32(val) for val in embedding]

        # Update the item with the corrected embedding
        item['vector'] = embedding
        fixed_items.append(item)

    return fixed_items
def query_chroma(form_data: QueryCollectionsForm, hybrid=False):
    try:
        if hybrid or len(form_data.collection_names) > 1:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_chroma_embeddings,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function="",
                r=(
                    form_data.r if form_data.r else 0.0
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_chroma_embeddings,
                k=form_data.k if form_data.k else 3,
            )

    except Exception as e:
        log.exception(e)
        return {}

""" -> private BATCH LOADER HELPER <- """
def store_data_in_vector_db(data, collection_name, metadata: Optional[dict] = None, overwrite: bool = True) -> tuple[bool, None]:
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
""" -> private BATCH LOADER HELPER <- """
def store_text_in_vector_db(text, metadata, collection_name, overwrite: bool = False) -> bool:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.config.CHUNK_SIZE,
        chunk_overlap=app.state.config.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])
    return __store_docs_in_vector_db(docs, collection_name, overwrite=overwrite)
""" -> private HELPER <- """
def __store_docs_in_vector_db(docs, collection_name, metadata: Optional[dict] = None, overwrite: bool = True) -> bool:
    log.info(f"store_docs_in_vector_db {docs} {collection_name}")
    from assistant.ollama_client import generate_ollama_embedding
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
            print("Inserting document into chromadb")
            items = [
                        {
                            "id": str(uuid.uuid4()),
                            "text": text,
                            "vector": generate_chroma_embeddings(text=text),
                            "metadata": metadatas[idx],
                        }
                        for idx, text in enumerate(texts)
                    ]
            # new_items = __validate_and_fix_embeddings(items)
            VECTOR_DB_CLIENT.insert(
                collection_name=collection_name,
                items=items,
            )
            return True
    except Exception as e:
        log.exception(e)
        return False
""" -> private DATA LOADER HELPER <- """
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

    if (app.state.config.CONTENT_EXTRACTION_ENGINE == "tika" and app.state.config.TIKA_SERVER_URL):
        if file_ext in known_source_ext or (file_content_type and file_content_type.find("text/") >= 0):
            loader = TextLoader(file_path, autodetect_encoding=True)
        else:
            loader = TikaLoader(file_path, file_content_type)
    else:
        if file_ext == "pdf":
            loader = PyPDFLoader(file_path, extract_images=app.state.config.PDF_EXTRACT_IMAGES)
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
        elif (file_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_ext == "docx"):
            loader = Docx2txtLoader(file_path)
        elif file_content_type in [ "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",] or file_ext in ["xls", "xlsx"]:
            loader = UnstructuredExcelLoader(file_path)
        elif file_content_type in ["application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",] or file_ext in ["ppt", "pptx"]:
            loader = UnstructuredPowerPointLoader(file_path)
        elif file_ext == "msg":
            loader = OutlookMessageLoader(file_path)
        elif file_ext in known_source_ext or (file_content_type and file_content_type.find("text/") >= 0):
            loader = TextLoader(file_path, autodetect_encoding=True)
        else:
            loader = TextLoader(file_path, autodetect_encoding=True)
            known_type = False

    return loader, known_type

""" -> public INTAKE <- """
def store_doc(collection_name: Optional[str], file: RaiPath):
    log.info(f"Processing file: {file}")
    try:
        filename = file.file_name

        # Guess the content type based on the file extension
        content_type, encoding = mimetypes.guess_type(file.path)
        log.info(f"Detected content_type: {content_type}")

        if collection_name is None:
            with open(file.path, "rb") as f:
                collection_name = calculate_sha256(f)[:63]

        loader, known_type = get_loader(filename, content_type, file.path)
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
            else:
                return {}
        except Exception as e:
            log.exception(e)
            return {}
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            return {}
        else:
            return {}
def store_text(form_data: TextRAGForm, created_by:str):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)

    result = store_text_in_vector_db(
        form_data.content,
        metadata={ "name": form_data.name, "created_by": created_by },
        collection_name=collection_name,
    )

    if result: return {"status": True, "collection_name": collection_name}
    else: return {"status": False, "collection_name": collection_name}
""" -> public SCAN <- """
def scan_docs_dir(collection_name, file_path="/Users/chazzromeo/Desktop/data"):
    for path in Path(file_path).rglob("./**/*"):
        try:
            if path.is_file() and not path.name.startswith("."):
                tags = extract_folders_after_data_docs(path)
                filename = path.name
                file_content_type = mimetypes.guess_type(path)

                f = open(path, "rb")
                if collection_name is None:
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

if __name__ == "__main__":
    # scan_docs_dir(collection_name="nebie")
    results = query_chroma(
        form_data=QueryCollectionsForm(
            collection_names=["pcsc-main"],
            query="player code of conduct is"
        ),
        hybrid=True
    )
    print(results)

