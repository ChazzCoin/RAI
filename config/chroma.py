from asyncio import to_thread

import chromadb
from F import DICT, DATE
from chromadb.config import Settings
from dotenv import load_dotenv
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from assistant import openai_client as openai
from dataset.TextCleaner import TextCleaner
from typing import List, Dict
import asyncio
from functools import wraps
from F.CLASS.Function import FairFunction
from F.CLASS.Routines import FairRoutine
# Load environment variables from a .env file
load_dotenv()
from F.LOG import Log
LOG = Log("ChromaDB")
# Setup basic logging
logging.basicConfig(level=logging.INFO)

DOCUMENT_TEMPLATE = lambda id, text, metadata, embeddings: { 'id': id, 'text': text, 'metadata': metadata, 'embeddings': embeddings }

MetaData = lambda topic, source, author, date: { "Topic": topic, "Source": source, "Author": author, "Date": date }
Document = lambda content, metadata: { "content": content, "metadata": metadata }
""" Example ChromaDB Document:
{
    "id": "unique id",
    "text": "raw text being inputted",
    "metadata": {
        "title": "title of record",
        "date": "date of record",
        "topic": "topic of record",
        "url": "url if available",
    },
    "embeddings": ""
}
"""

class ChromaDocument:
    id: str
    text: str
    metadata: dict
    embeddings:list = []
    meta_title: str = ""
    meta_topic: str = ""
    meta_url: str = ""

    def __init__(self, id:str, text:str, metadata:dict, embeddings:list=[]):
        self.id = id
        self.text = text
        self.metadata = metadata
        self.embeddings = embeddings

    def metadata(self, title:str, topic:str, url:str):
        self.meta_title = title
        self.meta_topic = topic
        self.meta_url = url

    def toJson(self, embeddings:list=None):
        return {
            "id": self.id,
            "text": self.text,
            "metadata": {
                "title": self.meta_title,
                "date": DATE.get_now_month_day_year_str(),
                "topic": self.meta_topic,
                "url": self.meta_url,
            },
            "embeddings": self.embeddings if embeddings is None else embeddings
        }

def async_run_in_executor(func):
    """Decorator to run a function in an asyncio executor."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor()
        # Run the original function in the executor
        result = await loop.run_in_executor(executor, func, *args, **kwargs)
        # Shutdown the executor after the task is complete
        executor.shutdown(wait=True)
        return result
    return wrapper

# @async_run_in_executor
def base_embedding(text_in):
    cleaned_text = TextCleaner.clean_text_for_openai_embedding(text_in)
    print("Cleaned Text for Embedding:", cleaned_text)
    embeddings = openai.generate_embeddings(cleaned_text)
    return embeddings

class AsyncChromaDBClient:
    """An asynchronous wrapper for the ChromaDB client."""
    def __init__(self, settings=None):
        self.settings = settings or Settings(
            chroma_server_host=os.getenv("DEFAULT_CHROMA_SERVER_HOST"),
            chroma_server_http_port=os.getenv("DEFAULT_CHROMA_SERVER_PORT"),
            persist_directory=os.getenv("DEFAULT_CHROMA_CACHE_FOLDER"),
            is_persistent=True,
        )
        self.client = chromadb.Client(self.settings)
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor()
        LOG.i("Initialized AsyncChromaDBClient")

    @staticmethod
    async def base_embedding(text_in):
        # Assuming TextCleaner.clean_text_for_openai_embedding is a synchronous function
        # If this function is also I/O bound, it should be refactored as an async function too.
        loop = asyncio.get_running_loop()

        # Run the synchronous cleaning function in the executor
        cleaned_text = await loop.run_in_executor(None, TextCleaner.clean_text_for_openai_embedding, text_in)
        print("Cleaned Text for Embedding:", cleaned_text)

        # Run the synchronous embedding function in the executor
        embeddings = await loop.run_in_executor(None, openai.generate_embeddings, cleaned_text)

        return embeddings

    async def add_documents(self, collection_name: str, documents: dict):
        """Asynchronously add documents to a collection."""
        def _add():
            try:
                collection = self.client.get_or_create_collection(name=collection_name)
                collection.add(**documents)
                LOG.i(f"Added documents to collection '{collection_name}'")
            except Exception as e:
                LOG.i(f"Failed to add documents: {e}")
                raise

        await self.loop.run_in_executor(self.executor, _add)

    async def query(self, user_input: str, n_results: int = 3, collection_name: str = "web_pages_2", debug: bool = False):
        """Asynchronously query documents from a collection."""
        user_embedding = await self.base_embedding(user_input)
        async def _query():
            try:
                collection = self.client.get_or_create_collection(name=collection_name)
                lp = asyncio.get_running_loop()
                q = {
                    "query_embeddings":[user_embedding],
                    "n_results":n_results
                }
                results = await lp.run_in_executor(self.executor, collection.query, q)
                # results = collection.query(
                #     query_embeddings=[user_embedding],
                #     n_results=n_results
                # )

                metadata = results.get('metadatas', [])[0]
                LOG.i(f"Queried documents from collection '{collection_name}' - {results}")
                if debug:
                    for doc in metadata:
                        print(DICT.get("title", doc, ""))
                        print(DICT.get("topic", doc, ""))
                        print(DICT.get("url", doc, ""))
                        print(DICT.get("date", doc, ""))
                return metadata
            except Exception as e:
                LOG.i(f"Failed to query documents: {e}")
                raise
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, _query)

    def squery(self, user_input: str, n_results: int = 3, collection_name: str = "web_pages_2", debug: bool = False):
        """Asynchronously query documents from a collection."""
        try:
            collection = self.client.get_or_create_collection(name=collection_name)
            user_embedding = base_embedding(user_input)
            results = collection.query(
                query_embeddings=[user_embedding],
                n_results=n_results
            )
            LOG.i(f"Queried documents from collection '{collection_name}'")
            metadata = results.get('metadatas', [])[0]
            if debug:
                for doc in metadata:
                    print(DICT.get("title", doc, ""))
                    print(DICT.get("topic", doc, ""))
                    print(DICT.get("url", doc, ""))
                    print(DICT.get("date", doc, ""))
            return metadata
        except Exception as e:
            LOG.i(f"Failed to query documents: {e}")
            return {}



    async def shutdown(self):
        """Shut down the executor."""
        LOG.i("Shutting down AsyncChromaDBClient")
        self.executor.shutdown(wait=True)

from F import OS


class ChromaInstance:
    chroma_client: chromadb.Client
    collection: chromadb.Collection

    def __init__(self, collection_name:str=None, persistent:bool=True):
        try:
            print("Chroma Host:", os.getenv("DEFAULT_CHROMA_SERVER_HOST"))
            print("Chroma Port:", os.getenv("DEFAULT_CHROMA_SERVER_PORT"))
            print("Cached Directory:", os.path.dirname(os.path.abspath(__file__)))
            self.chroma_client = chromadb.Client(Settings(
                chroma_server_host=os.getenv("DEFAULT_CHROMA_SERVER_HOST"),
                chroma_server_http_port=os.getenv("DEFAULT_CHROMA_SERVER_PORT"),
                persist_directory=f"/python-docker/assistant/chroma",
                is_persistent=persistent,
            ))
            if collection_name:
                self.set_collection(collection_name)
            else:
                self.set_collection(os.getenv("DEFAULT_CHROMA_COLLECTION"))
        except Exception as e:
            print(f"Failed to initialize ChromaInstance: {e}")
            raise e

    def set_collection(self, collection_name: str):
        try:
            self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
            print(f"Connected to collection: {collection_name}")
        except Exception as e:
            print(f"Failed to set or create collection: {e}")
            raise e

    @staticmethod
    def base_embedding(text_in):
        cleaned_text = TextCleaner.clean_text_for_openai_embedding(text_in)
        print("Cleaned Text for Embedding:", cleaned_text)
        embeddings = openai.generate_embeddings(cleaned_text)
        return embeddings

    def chromadb_query_wrapper(self, embedding):
        """Wrapper function to query ChromaDB synchronously."""
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=10
        )

    async def query_chromadb(self, embedding, collection_name:str=None):
        """Asynchronously query ChromaDB using embeddings."""
        if collection_name:
            self.set_collection(collection_name)
        print("Querying Collection", self.collection.name)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self.chromadb_query_wrapper,
            embedding
        )
        print(f"Query Results: {str(results)}")
        return results

    def query(self, user_input: str, n_results: int = 3, debug: bool = True):
        # Generate embedding for the user input using OpenAI embeddings
        user_embedding = self.base_embedding(user_input)
        # Query ChromaDB for similar documents
        print(self.collection.name)
        results = self.collection.query(
            query_embeddings=[user_embedding],
            n_results=n_results
        )
        # Extract the relevant documents and metadata
        metadata = results.get('metadatas', [])[0]
        if debug:
            for doc in metadata:
                print(DICT.get("title", doc, ""))
                print(DICT.get("topic", doc, ""))
                print(DICT.get("url", doc, ""))
                print(DICT.get("date", doc, ""))
        return metadata

    """ Base Add/Insert Function """
    def add_chroma_documents(self, *documents: ChromaDocument) -> None:
        for doc in documents:
            # Generate embeddings using OpenAI
            embeddings = self.base_embedding(doc.text)
            # Add the embeddings and document to the ChromaDB collection
            self.__base_insert(doc.toJson(embeddings))
        print(f"Added {len(documents)} documents to ChromaDB.")

    def add_documents(self, documents: List[Dict[str, str]]) -> None:
        for doc in documents:
            # Generate embeddings using OpenAI
            embeddings = self.base_embedding(doc['text'])
            document = DOCUMENT_TEMPLATE(doc['id'], doc['text'], doc.get('metadata', {}), embeddings)
            # Add the embeddings and document to the ChromaDB collection
            self.__base_insert(document)
        print(f"Added {len(documents)} documents to ChromaDB.")

    def __base_insert(self, document: dict):
        try:
            self.__insert(
                doc_id=document.get("id"),
                doc_text=document.get("text"),
                metadata=document.get("metadata"),
                embeddings=document.get("embeddings")
            )
            print(f"Document {document.get('id')} added to collection.")
        except KeyError as e:
            print(f"Document format error: missing {e}")
            raise e

    def __insert(self, doc_id: str, doc_text: str, metadata: dict, embeddings: list = None):
        try:
            # Insert document with optional embeddings
            self.collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id],
                embeddings=[embeddings] if embeddings else None
            )
            print(f"Document {doc_id} added to collection.")
        except Exception as e:
            print(f"Failed to insert document {doc_id}: {e}")
            raise e

    """ --------- Untested --------- """
    def get_all_collections(self):
        try:
            # Retrieve all documents from the collection
            results = self.chroma_client.list_collections()
            # Check if any documents were found
            if results:
                LOG.s(f"Retrieved {len(results)} collections from the database.")
                return results
            else:
                LOG.w("No collections found in the database.")
                return []
        except Exception as e:
            LOG.e(f"Failed to retrieve documents from collection: {e}")
            raise e

    def get_all_documents(self):
        try:
            # Retrieve all documents from the collection
            results = self.collection.get()
            # Check if any documents were found
            if results and 'documents' in results:
                LOG.s(f"Retrieved {len(results['documents'])} documents from the collection.")
                return results['documents']
            else:
                LOG.w("No documents found in the collection.")
                return []
        except Exception as e:
            LOG.e(f"Failed to retrieve documents from collection: {e}")
            raise e

    def get_document_by_id(self, doc_id: str):
        try:
            results = self.collection.get(ids=[doc_id])
            if results:
                logging.info(f"Document {doc_id} retrieved.")
                return results
            else:
                logging.warning(f"Document {doc_id} not found.")
                return None
        except Exception as e:
            logging.error(f"Failed to retrieve document {doc_id}: {e}")
            raise e

    def delete_collection(self, collection_name: str):
        try:
            self.chroma_client.delete_collection(collection_name)
            logging.info(f"Collection {collection_name} deleted from database.")
        except Exception as e:
            logging.error(f"Failed to delete collection {collection_name}: {e}")
            raise e

    def delete_all_collections(self, *skip):
        try:
            for c in self.get_all_collections():
                name = c.name
                if name in skip:
                    continue
                self.chroma_client.delete_collection(name)
            logging.info(f"All Collections Deleted!")
        except Exception as e:
            logging.error(f"Failed to delete all collections: {e}")
            raise e

    def delete_document(self, doc_id: str):
        try:
            self.collection.delete(ids=[doc_id])
            logging.info(f"Document {doc_id} deleted from collection.")
        except Exception as e:
            logging.error(f"Failed to delete document {doc_id}: {e}")
            raise e

