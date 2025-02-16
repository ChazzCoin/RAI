import uuid

import numpy as np
from typing import Dict, Any, List

from F import DICT
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from rai.RAG.QHelp import DocumentQueryUtils
from rai.assistant.openai_client import generate_embeddings  # your embedding function
from F.LOG import Log

from rai.data.utilities.DataUtilities import ensure_string_for_chroma
from rai.data.utilities.text_data import schedule_text
from rai.internal.redisdb import RedisClient

Log = Log("VectorCache")


class VectorCache(RedisClient, DocumentQueryUtils):
    index_name = "rai_vector_cache"
    distance_metric = "COSINE"

    @classmethod
    def create(cls, index:str):
        cache = cls()
        return cache.create_index(index)

    @classmethod
    def search(cls, index:str, query:str):
        cache = cls()
        return cache.query(index, query)

    @classmethod
    def add(cls, index:str, text:str, metadata={}):
        cache = cls()
        return cache.add_text(index, text, metadata)

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

    def add_text(self, index, text: str, metadata={}):
        set_id = f"doc:{index}:{str(uuid.uuid4())}"
        try:
            response = generate_embeddings(text)
            embeddings = np.array(response, dtype=np.float32)
            pipe = self.redis_client.pipeline()
            meta = DICT.lazy_merge_dicts(metadata, {
                "index": index,
                "set_id": set_id,
            })
            pipe.hset(set_id, mapping={
                "vector": embeddings.tobytes(),
                "content": text,
                "metadata": str(ensure_string_for_chroma(meta)),
                "tag": index
            })
            res = pipe.execute()
            print(f"Document '{set_id}' stored successfully.")
            return res
        except Exception as e:
            print(f"Failed to store document '{set_id}': {e}")

    def query(self, index, query) -> List[Dict[str, Any]]:
        embeddings = generate_embeddings(query)
        query_embedding = np.array(embeddings, dtype=np.float32)
        tag = "(@tag: { " + index + " } )"
        try:
            redis_query = (
                Query(f"{tag}=>[KNN 2 @vector $vec as score]")
                .sort_by("score")
                .return_fields("content", "tag", "score", "metadata")
                .paging(0, 2)
                .dialect(2)
            )
            query_params = {"vec": query_embedding.tobytes()}
            documents = self.redis_client.ft(self.index_name).search(redis_query, query_params).docs
            return documents
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []

    def get_all_documents_in_index(self, index):
        try:
            docs = self.keys(f"*{index}*")
            return docs
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []

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