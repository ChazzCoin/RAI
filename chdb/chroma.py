import chromadb
from F import DICT, DATE
from dotenv import load_dotenv
import os
import logging
from rai.data.TextCleaner import TextCleaner
from rai.assistant import openai_client as openai
from typing import List, Dict
import asyncio


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

class ChromaInstance:
    chroma_client: chromadb.HttpClient
    collection: chromadb.Collection

    def __init__(self, collection_name:str=None, persistent:bool=True):
        try:
            self.chroma_client = chromadb.HttpClient(
                host=os.getenv("DEFAULT_CHROMA_SERVER_HOST"),
                port=int(os.getenv("DEFAULT_CHROMA_SERVER_PORT"))
            )
        except Exception as e:
            print(f"Failed to initialize ChromaInstance: {e}")
            raise e
    async def getClient(self):
        self.chroma_client = await chromadb.AsyncHttpClient(host='localhost', port=8000)
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

    def chromadb_query_wrapper(self, embedding, collection):
        """Wrapper function to query ChromaDB synchronously."""
        collect = self.chroma_client.get_or_create_collection(collection)
        return collect.query(
            query_embeddings=[embedding],
            n_results=50
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
            embedding, collection_name
        )
        print(f"Query Results: {str(results)}")
        return results

    def query(self, collection, user_input: str, n_results: int = 3, debug: bool = True):
        # Generate embedding for the user input using OpenAI embeddings
        user_embedding = self.base_embedding(user_input)
        # Query ChromaDB for similar documents
        print(f"Query ChromaDB: {self.collection.name}")
        collect = self.chroma_client.get_or_create_collection(collection)
        results = collect.query(
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
        return results

    def get_all_documents_merge(self):
        try:
            # Retrieve all documents, including their ids, texts, metadata, and embeddings
            results = self.collection.get()
            if results and 'documents' in results:
                documents = []
                for i, doc_text in enumerate(results['documents']):
                    doc = {
                        'id': results['ids'][i],
                        'text': doc_text,
                        'metadata': results['metadatas'][i] if 'metadatas' in results else {},
                        'embeddings': results['embeddings'][i] if results.get('embeddings') else None
                    }
                    documents.append(doc)
                print(f"Retrieved {len(documents)} documents from the collection.")
                return documents
            else:
                print("No documents found in the collection.")
                return []
        except Exception as e:
            print(f"Failed to retrieve documents from collection: {e}")
            raise e

    def merge_collections(self, source_collection_name: str, target_collection_name: str):
        """Merge all documents from source collection into the target collection."""
        try:
            # Set the source collection
            self.set_collection(source_collection_name)
            source_documents = self.get_all_documents_merge()

            if not source_documents:
                print(f"No documents found in the source collection: {source_collection_name}")
                return

            # Set the target collection
            self.set_collection(target_collection_name)

            # Add all documents to the target collection
            for doc in source_documents:
                self.__insert(
                    doc_id=doc['id'],
                    doc_text=doc['text'],
                    metadata=doc.get('metadata', {}),
                    embeddings=doc.get('embeddings')
                )

            print(
                f"Successfully merged {len(source_documents)} documents from {source_collection_name} to {target_collection_name}.")

        except Exception as e:
            print(f"Failed to merge collections: {e}")
            raise e

    """ Base Add/Insert Function """
    def add_chroma_documents(self, collection, *documents: ChromaDocument) -> None:
        for doc in documents:
            # Generate embeddings using OpenAI
            embeddings = self.base_embedding(doc.text)
            # Add the embeddings and document to the ChromaDB collection
            self.__base_insert(collection, doc.toJson(embeddings))
        print(f"Added {len(documents)} documents to ChromaDB.")

    def add_documents(self, collection, documents: List[Dict[str, str]]) -> None:
        for doc in documents:
            # Generate embeddings using OpenAI
            embeddings = self.base_embedding(doc['text'])
            document = DOCUMENT_TEMPLATE(doc['id'], doc['text'], doc.get('metadata', {}), embeddings)
            # Add the embeddings and document to the ChromaDB collection
            self.__base_insert(collection, document)
        print(f"Added {len(documents)} documents to ChromaDB.")

    def __base_insert(self, collection, document: dict):
        try:
            self.__insert(
                collection=collection,
                doc_id=document.get("id"),
                doc_text=document.get("text"),
                metadata=document.get("metadata"),
                embeddings=document.get("embeddings")
            )
            print(f"Document {document.get('id')} added to collection.")
        except KeyError as e:
            print(f"Document format error: missing {e}")
            raise e

    def __insert(self, collection, doc_id: str, doc_text: str, metadata: dict, embeddings: list = None):
        try:
            # Insert document with optional embeddings
            collect = self.chroma_client.get_collection(collection)
            collect.add(
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

    def get_all_documents(self, collection):
        try:
            # Retrieve all documents from the collection
            collect = self.chroma_client.get_collection(name=collection)
            results = collect.get()
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

if __name__ == '__main__':
    chroma = ChromaInstance(collection_name="parkcitysc-new")
    # print(chroma.query("parkcitysc-new", "Quinns Field D 2024-08-12"))
    print(chroma.get_all_documents("parkcitysc-new"))
    # print(chroma.chroma_client.list_collections())