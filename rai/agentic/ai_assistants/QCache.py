import uuid

from typing import Dict, Any, List

from F import DICT
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from rai.RAG.QHelp import DocumentQueryUtils
from rai.assistant.connectors import rAI
from F.LOG import Log

from rai.ingest.IngestModels import IngestLoaderDocument
from rai.ingest.utilities.DataUtilities import ensure_metadata_is_string_for_chroma
from rai.ingest.utilities.text_data import schedule_text
from rai.internal.redis_db import RedisClient

Log = Log("VectorCache")


class VectorCache(RedisClient, rAI, DocumentQueryUtils):
    index_name = "rai_vector_cache"
    distance_metric = "COSINE"

    @classmethod
    def create(cls):
        cache = cls()
        return cache.create_index()

    @classmethod
    def search(cls, prefix:str, query:str):
        cache = cls()
        return cache.query(prefix, query)

    @classmethod
    def add(cls, prefix:str, text:str, metadata={}):
        cache = cls()
        return cache.add_text(prefix, text, metadata)

    # -------------------------------------------------------------------------
    # Vector-Based Functions (Redis/RediSearch operations)
    # -------------------------------------------------------------------------
    def create_index(self):
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
            # create Index
            self.redis_client.ft(self.index_name).create_index(fields=schema, definition=definition)
            print(f"Index '{self.index_name}' created successfully.")
        except Exception as e:
            print(f"Index '{self.index_name}' may already exist. Details: {e}")

    def add_text(self, prefix, text: str, metadata={}):
        set_id = f"doc:{prefix}:{str(uuid.uuid4())}"
        try:
            meta = DICT.lazy_merge_dicts(metadata, {
                "index": prefix,
                "set_id": set_id,
            })
            return self.redis_client.hset(set_id, mapping={
                "vector": self.embed_for_cache(text),
                "text": text,
                "metadata": str(ensure_metadata_is_string_for_chroma(meta)),
                "tag": prefix
            })
        except Exception as e:
            print(f"Failed to store document '{set_id}': {e}")

    def add_doc(self, prefix, doc: {}):
        set_id = f"doc:{prefix}:{str(uuid.uuid4())}"
        try:
            return self.redis_client.hset(set_id, mapping={
                "vector": self.embed_for_cache(doc.page_content),
                "text": doc.page_content,
                "metadata": str(ensure_metadata_is_string_for_chroma(doc.metadata)),
                "tag": prefix
            })
        except Exception as e:
            print(f"Failed to store document '{set_id}': {e}")

    def query(self, prefix, query) -> List[Dict[str, Any]]:
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

    def get_all_documents_in_index(self, prefix):
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
    import time
    # Initialize VectorCache with a test index.
    vector_cache = VectorCache()
    results = vector_cache.get_all_documents_in_index("pcsc2025")
    print(results)
    # vector_cache.create_index("pcsc2025")

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