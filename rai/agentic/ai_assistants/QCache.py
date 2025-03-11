import uuid
from datetime import datetime

from typing import Dict, Any, List

import numpy as np
from F import DICT
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from rai.RAG.QHelp import DocumentQueryUtils
from F.LOG import Log

from rai.assistant.openai_client import generate_embeddings
from rai.ingest.utilities.IngestModels import IngestLoaderDocument
from rai.ingest.utilities.DataUtilities import ensure_metadata_format_for_chroma
from rai.ingest.utilities.text_data import schedule_text
from rai.internal.redis_db import RedisClient

Log = Log("VectorCache")


class VectorCache(RedisClient, DocumentQueryUtils):
    index_name = "rai_vector_cache"
    distance_metric = "COSINE"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect()

    @classmethod
    def create(cls):
        cache = cls()
        return cache.create_index()

    @classmethod
    def search(cls, prefix:str, query:str):
        cache = cls()
        return cache.query(prefix, query)

    @classmethod
    def add(cls, prefix:str, text:str, **metadata):
        cache = cls()
        return cache.add_text(prefix, text, **metadata)

    # -------------------------------------------------------------------------
    # Vector-Based Functions (Redis/RediSearch operations)
    # -------------------------------------------------------------------------
    def create_index(self):
        """ Create a new Index for vector storage """
        try:
            schema = (
                TagField("tag"),  # Tag Field Name
                VectorField(
                    "vector",  # Vector Field Name
                "FLAT",
                {
                            "TYPE": "FLOAT32",  # FLOAT32 or FLOAT64
                            "DIM": 3072,  # Number of Vector Dimensions
                            "DISTANCE_METRIC": "COSINE",  # Vector Search Distance Metric
                         }
                ),
            )
            # index Definition
            definition = IndexDefinition(prefix=["doc:"], index_type=IndexType.HASH)
            self.redis_client.ft(self.index_name).create_index(fields=schema, definition=definition)
            print(f"Index '{self.index_name}' created successfully.")
        except Exception as e:
            print(f"Index '{self.index_name}' may already exist. Details: {e}")

    def embed_for_cache(self, query:str) -> bytes:
        """ Generate Embeddings from Text/Query Input """
        embeddings = generate_embeddings(query)
        query_embedding = np.array(embeddings, dtype=np.float32)
        return query_embedding.tobytes()

    def add_text(self, prefix, text: str, **metadata):
        """ Add new text:str to vector cache storage """
        set_id = f"doc:{prefix}:{str(uuid.uuid4())}"
        try:
            meta = DICT.lazy_merge_dicts(metadata, {
                "index": prefix,
                "set_id": set_id,
            })
            return self.redis_client.hset(set_id, mapping={
                "vector": self.embed_for_cache(text),
                "text": text,
                "metadata": str(ensure_metadata_format_for_chroma(meta)),
                "tag": prefix
            })
        except Exception as e:
            return f"Failed to store document '{str(set_id)}': {str(e)}"

    def add_doc(self, prefix, doc: {}):
        """ Add new doc:{}/dict to vector cache storage """
        set_id = f"doc:{prefix}:{str(uuid.uuid4())}"
        try:
            return self.redis_client.hset(set_id, mapping={
                "vector": self.embed_for_cache(doc.page_content),
                "text": doc.page_content,
                "metadata": str(ensure_metadata_format_for_chroma(doc.metadata)),
                "tag": prefix
            })
        except Exception as e:
            print(f"Failed to store document '{set_id}': {e}")
            return None

    def query(self, prefix, query) -> List[Dict[str, Any]]:
        """ Query/Search the vector cache storage by collection/prefix name """
        tag = "(@tag: { " + prefix + " } )"
        try:
            redis_query = (
                Query(f"{tag}=>[KNN 2 @vector $vec as score]")
                .sort_by("score")
                .return_fields("text", "tag", "score", "metadata")
                .paging(0, 2)
                .dialect(2)
            )
            query_params = {"vec": self.embed_for_cache(query)}
            documents = self.redis_client.ft(self.index_name).search(redis_query, query_params).docs
            return documents
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []


    def get_documents_by_tag(self, tag: str, limit=10) -> List[Dict[str, Any]]:
        """Retrieve documents based on a specific tag."""
        try:
            redis_query = (
                Query(f"@tag:{{{tag}}}")
                .return_fields("text", "tag", "metadata")
                .paging(0, limit)
                .dialect(2)
            )
            results = self.redis_client.ft(self.index_name).search(redis_query).docs
            return results
        except Exception as e:
            print(f"Error retrieving documents by tag '{tag}': {e}")
            return []

    def get_documents_by_prefix(self, prefix: str, limit=10) -> List[Dict[str, Any]]:
        """Retrieve documents based on key prefix."""
        try:
            redis_query = (
                Query(f"@__key:doc\\:{prefix}\\:*")
                .return_fields("text", "tag", "metadata")
                .paging(0, limit)
                .dialect(2)
            )
            results = self.redis_client.ft(self.index_name).search(redis_query).docs
            return results
        except Exception as e:
            print(f"Error retrieving documents by prefix '{prefix}': {e}")
            return []

    def get_all_documents_in_index(self, prefix):
        """ Get All Documents in vector cache storage by collection/prefix name """
        try:
            docs = self.keys(f"*{prefix}*")
            return docs
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []

    def caches(self, prefix, docs: List[IngestLoaderDocument]):
        for doc in docs: self.cache(prefix, doc)

    def cache(self, prefix, doc: IngestLoaderDocument):
        return self.add_doc(prefix, doc)


def test_vector_cache():
    # Initialize VectorCache with a test index.
    vector_cache = VectorCache()
    # results = vector_cache.create_index()
    results = vector_cache.query("rai2025", "note")
    # results = vector_cache.get_all_documents_in_index("rai2025")
    # results = vector_cache.add_text("rai2025", "this is a test note", timestamp=int(datetime.utcnow().timestamp()))
    print(results)
    #

    # Create a random embedding for testing.
    doc_text = schedule_text
    metadata = {"category": "test", "author": "unit tester"}

    # --- Store the document ---
    # print("\n[STORE] Storing document...")
    # vector_cache.add_text("pcsc2025", doc_text)

    # --- Query by embedding ---
    # print("\n[QUERY] Querying by embedding...")
    # query_results = vector_cache.query("pcsc2025", "when are placements posted?")
    # print("Query Results:", query_results)




if __name__ == "__main__":
    test_vector_cache()