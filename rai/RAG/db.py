from __future__ import annotations
import os
import chromadb
from chromadb import Settings
from chromadb.utils.batch_utils import create_batches
from typing import Optional
from rai.RAG.models import VectorItem, SearchResult, GetResult

# Chroma
CHROMA_DATA_PATH = f"/chroma"
CHROMA_TENANT = os.environ.get("CHROMA_TENANT", chromadb.DEFAULT_TENANT)
CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE)
CHROMA_HTTP_HOST = os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "192.168.1.6")
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

class ChromaClient:
    def __init__(self, host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT):
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            headers=CHROMA_HTTP_HEADERS,
            ssl=CHROMA_HTTP_SSL,
            tenant=chromadb.DEFAULT_TENANT,
            database=chromadb.DEFAULT_DATABASE,
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )
        print("Chroma Host:", CHROMA_HTTP_HOST)
        print("Chroma Port:", CHROMA_HTTP_PORT)
        print("Chroma Database:", CHROMA_DATABASE)
        print("Chroma Tenant:", CHROMA_TENANT)

        # else:
            # self.client = chromadb.PersistentClient(
            #     path=CHROMA_DATA_PATH,
            #     settings=Settings(allow_reset=True, anonymized_telemetry=False),
            #     tenant=CHROMA_TENANT,
            #     database=CHROMA_DATABASE,
            # )

    def has_collection(self, collection_name: str) -> bool:
        # Check if the collection exists based on the collection name.
        collections = self.client.list_collections()
        return collection_name in [collection.name for collection in collections]

    def delete_collection(self, collection_name: str):
        # Delete the collection based on the collection name.
        return self.client.delete_collection(name=collection_name)

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        # Search for the nearest neighbor items based on the vectors and return 'limit' number of results.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.query(
                query_embeddings=vectors,
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

    def get(self, collection_name: str) -> Optional[GetResult]:
        # Get all the items in the collection.
        collection = self.client.get_collection(name=collection_name)
        if collection:
            result = collection.get()
            return GetResult(
                **{
                    "ids": [result["ids"]],
                    "documents": [result["documents"]],
                    "metadatas": [result["metadatas"]],
                }
            )
        return None

    def insert(self, collection_name: str, items: list[VectorItem]):
        # Insert the items into the collection, if the collection does not exist, it will be created.
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [item["id"] for item in items]
        documents = [item["text"] for item in items]
        embeddings = [item["vector"] for item in items]
        metadatas = [item["metadata"] for item in items]

        # embeddings = [
        #     item["vector"].astype(np.int32).tolist() if isinstance(item["vector"], np.ndarray) else item["vector"]
        #     for item in items
        # ]

        for batch in create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        ):
            collection.add(*batch)

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

    def reset(self):
        # Resets the database. This will delete all collections and item entries.
        return self.client.reset()

if __name__ == "__main__":
    client = ChromaClient()
    print(client.has_collection("pcsc-main"))
    results = client.get("pcsc-main")
    print(results)