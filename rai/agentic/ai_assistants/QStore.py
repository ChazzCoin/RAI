import threading
import uuid
from typing import List, Dict

from tqdm import tqdm
from typing_extensions import Any  # noqa: F401

from rai.RAG.QHelp import DocumentQueryUtils
from rai.RAG.models import VectorItem, StoreDocument
from rai.assistant.connectors import LLM
from rai.ingest.utilities.IngestModels import IngestLoaderDocument
from rai.ingest.utilities.DataUtilities import ensure_metadata_format_for_chroma
from rai.internal.chromadb import ChromaClient
from F.LOG import Log

from rai.RAG.connectors import VECTOR_DB_CLIENT

Log = Log("Rai Data Loader")

R = LLM
###############################################################################
#                Chroma (Vector-Based) Query Handler                          #
###############################################################################
class VectorStore(ChromaClient, DocumentQueryUtils):
    """
    Contains all functions that perform vector-based (Chroma) queries.
    """
    def get_all(self, collection, limit:int=100, offset:int=0, where:dict={}, combined=False):
        results = self.get(collection, limit=limit, offset=offset, where=where, combined=combined)
        # Uses the document merging function from DocumentQueryUtils
        return DocumentQueryUtils.merge_sort_all_results(query_results=[results.model_dump()])

    @staticmethod
    def get_available_sub_collections(prefix:str) -> [str]:
        return VECTOR_DB_CLIENT.get_all_sub_collections(prefix=prefix)
    @staticmethod
    def get_all_from_store(collection:str, limit:int=100, offset:int=0, where:dict={}, combined=False) -> List[StoreDocument]:
        results = VECTOR_DB_CLIENT.get(collection, limit=limit, offset=offset, where=where, combined=combined)
        merged_results = DocumentQueryUtils.merge_sort_all_results(query_results=[results.model_dump()])
        return [StoreDocument.model_validate(record) for record in merged_results]
    @classmethod
    def queries_store(cls, *collections:str, user_prompt: str, k: int = 5, where: dict = None) -> Dict[str, List[StoreDocument]]:
        query_results = {}

        def query_db(collection, user_prompt, where):
             query_results[collection] = cls.query_store(
                collection,
                user_message=user_prompt,
                k=k,
                where=where
            )

        threads = []
        for collection in collections:
            thread = threading.Thread(target=query_db, args=(collection, user_prompt, where))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        return query_results
    @staticmethod
    def query_store(collection, user_message: str, k: int = 100, where: dict = None) -> List[StoreDocument]:
        try:
            print("User Query:", user_message)
            results = VECTOR_DB_CLIENT.search_vector(
                collection_name=collection,
                vectors=[R.embed(user_message)],
                limit=k,
                where=where,
            )
            temp = DocumentQueryUtils.merge_sort_query_results(query_results=[results.model_dump()], k=k)
            return [StoreDocument.model_validate(record) for record in temp]
        except Exception as e:
            Log.e("Failed to query", e)
            return []
    @staticmethod
    def prepare_for_store(prefix:str, docs: List['IngestLoaderDocument']):
        items = {}
        for idx, doc in enumerate(tqdm(docs, desc="Preparing Documents.", colour="yellow")):
            temp = {
                "id": f"{str(uuid.uuid4())}:{str(idx)}",
                "text": str(doc.page_content),
                "vector": R.embed(text=doc.page_content),
                "metadata": ensure_metadata_format_for_chroma(doc.metadata),
                "tag": prefix
            }
            collection = doc.metadata.get('collection', 'general')
            c = f"{prefix}.{collection}"
            temp_items = items.get(c, [])
            temp_items.append(temp)
            items[c] = temp_items
        return items
    @staticmethod
    def stores(prefix:str, docs: List['IngestLoaderDocument']):
        sorted_documents: Dict[str:VectorItem] = VectorStore.prepare_for_store(prefix, docs)
        for collection, items in sorted_documents.items():
            Log.i(f"importing [ {len(items)} ] docs in [ {collection} ]")
            try:
                return VectorStore.store(collection, items)
            except Exception as e:
                Log.e(e)
    @staticmethod
    def store(collection:str, documents: List[VectorItem]):
        return VECTOR_DB_CLIENT.insert(
            collection_name=collection,
            items=documents,
        )
    @staticmethod
    def create_and_store(collection: str, id:str, text:str, metadata:dict):
        vector_document = VectorItem(
            id=id,
            text=text,
            vector=R.embed(text=text),
            metadata=metadata,
        )
        return VECTOR_DB_CLIENT.insert(
            collection_name=collection,
            items=[vector_document],
        )


vSTORE = VectorStore()

if __name__ == "__main__":
    # Instantiate the Chroma query handler
    chroma_handler = VectorStore()

    # Example: threaded query across several collections.
    results = chroma_handler.queries_store(
        "pcsc2025.2.web.pages",
        "pcsc2025.2.web.contacts",
        "pcsc2025.2.web.events",
        "pcsc2025.2.web.context_groups",
        "pcsc2025.2.web.summaries",
        user_prompt="Who is joel person?",
        k=1
    )
