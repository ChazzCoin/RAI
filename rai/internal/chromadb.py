from __future__ import annotations
import os
import chromadb
from chromadb import Settings
from chromadb.utils.batch_utils import create_batches
from typing import Optional, List, Union

from pydantic import ValidationError
from tqdm import tqdm
from rai.RAG.models import VectorItem, SearchResult, GetResult, StoreDocument
from F.LOG import Log

Log = Log("Chromadb Database Client")

# Chroma
CHROMA_DATA_PATH = f"/chroma"
CHROMA_TENANT = os.environ.get("CHROMA_TENANT", "")
CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", "")
CHROMA_HTTP_HOST = os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "local") # "local" -OR- os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "local")
CHROMA_HTTP_PORT = int(os.environ.get("DEFAULT_CHROMA_SERVER_PORT", 8000))

# Comma-separated list of header=value pairs
CHROMA_HTTP_HEADERS = os.environ.get("CHROMA_HTTP_HEADERS", "")
if CHROMA_HTTP_HEADERS:
    CHROMA_HTTP_HEADERS = dict(
        [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
    )
else:
    CHROMA_HTTP_HEADERS = None
CHROMA_HTTP_SSL = os.environ.get("CHROMA_HTTP_SSL", "false").lower() == "true"

class ChromaDB:
    client = None
    def __init__(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):
        self.init(host, port)

    def init(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):

        if CHROMA_HTTP_HOST == "local":
            Log.w("\n--Chroma PersistentClient--\n")
            self.client = chromadb.PersistentClient(
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )
            Log.s("Successfully Connected to Local Chromadb Client.")
        else:
            Log.w("\n--Chroma HttpClient--\n")
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=chromadb.DEFAULT_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(allow_reset=True, anonymized_telemetry=False),
            )
            Log.w("Chroma Host:", CHROMA_HTTP_HOST)
            Log.w("Chroma Port:", CHROMA_HTTP_PORT)
            Log.w("Chroma Database:", CHROMA_DATABASE)
            Log.w("Chroma Tenant:", CHROMA_TENANT)
            Log.s("Successfully Connected to Remote Chromadb Client.")

class ChromaClient(ChromaDB):

    def __init__(self):
        super().__init__()

    def get_all_collections_by_chain(self, *collection_paths: str):
        try:
            def chain_collection_names(*collection_names: str):
                collection_name = ""
                index = 0
                for c in collection_names:
                    if index == 0:
                        collection_name = c
                    else:
                        collection_name = f"{collection_name}.{c}"
                    index += 1
                return collection_name

            # Assuming you have a ChromaDB client instance named 'VECTOR_DB_CLIENT'
            collections = self.client.list_collections()
            collection_names = [collection.name for collection in collections]

            base_path = chain_collection_names(*collection_paths)
            # Filter by prefix if provided
            final_names = [col for col in collection_names if col.startswith(base_path)]

            return final_names

        except Exception as e:
            # Log error with proper context
            Log.e(f"Error retrieving collections from ChromaDB: {e}")
            return []

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collections = self.client.list_collections()
        return collection_name in [collection.name for collection in collections]

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(name=collection_name)

    def search_text(self, collection_name: str, texts: list[str], limit: int) -> Optional[SearchResult]:
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.query(
                query_texts=texts,
                n_results=limit,
            )

            return SearchResult(
                **{
                    "ids": result["ids"],
                    "distances": result["distances"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                }
            )
        return None
    def search_vector(self, collection_name: str, vectors: list[list[float]], limit: int, where:dict=None, combined=False):
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        collection = self.client.get_collection(name=collection_name)
        if collection:

            if not where:
                result = collection.query(
                    query_embeddings=vectors,
                    n_results=limit,
                )
            else:
                result = collection.query(
                    query_embeddings=vectors,
                    n_results=limit,
                    where=where,
                )
            getResult = SearchResult(
                **{
                    "ids": result["ids"],
                    "distances": result["distances"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                }
            )
            if combined: return self.parse_from_result_to_dict(getResult)
            return getResult
        return None

    def get(self, collection_name: str, combined=False):
        # Get all the items in the collection.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.get()
            getResult = GetResult(
                **{
                    "ids": [result["ids"]],
                    "documents": [result["documents"]],
                    "metadatas": [result["metadatas"]],
                }
            )
            if combined: return self.parse_from_result_to_dict(getResult)
            return getResult
        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(name=collection_name)

        if type(items[0]) in [VectorItem]:
            ids = [item.id for item in items]
            documents = [item.text for item in items]
            embeddings = [item.vector for item in items]
            metadatas = [item.metadata for item in items]
        else:
            ids = [item["id"] for item in items]
            documents = [item["text"] for item in items]
            embeddings = [item["vector"] for item in items]
            metadatas = [item["metadata"] for item in items]

        batches = create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        for batch in tqdm(batches, f"Inserting into [ {collection_name} ]", colour="green"):
            collection.add(*batch)
        Log.s(f"Added {len(batches)} batched document(s) into Chroma Collection:", collection_name)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        # Update the items in the collection, if the items are not present, insert them. If the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [item["metadata"] for item in items]

        collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def delete(self, collection_name: str, ids: list[str]):
        # Delete the items from the collection based on the ids.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            collection.delete(ids=ids)

    def reset(self): return self.client.reset()

    @staticmethod
    def parse_dict_to_store_document(doc_list: List[dict]) -> List[StoreDocument]:
        store_documents = []
        for doc in doc_list:
            try:
                store_doc = StoreDocument(**doc)
                store_documents.append(store_doc)
            except ValidationError as e:
                print(f"Validation error for document {doc.get('id', 'unknown')}: {e}")
        return store_documents

    @staticmethod
    def parse_from_result_to_dict(get_result: GetResult) -> List[dict]:
        flattened_ids = [item for sublist in get_result.ids for item in sublist] if get_result.ids else []
        flattened_documents = [doc for sublist in get_result.documents for doc in
                               sublist] if get_result.documents else []
        flattened_metadatas = [meta for sublist in get_result.metadatas for meta in
                               sublist] if get_result.metadatas else []

        if not (len(flattened_ids) == len(flattened_documents) == len(flattened_metadatas)):
            raise ValueError("Mismatched lengths in ids, documents, and metadatas")

        combined = [
            {
                "id": id_val,
                "document": doc,
                "metadata": meta
            }
            for id_val, doc, meta in zip(flattened_ids, flattened_documents, flattened_metadatas)
        ]

        return combined