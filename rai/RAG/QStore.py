import os
import threading
from typing import Optional, List, Dict, Any

from FNLP.Regex import Re
from F import DICT, LIST
from typing_extensions import Any  # noqa: F401

from rai.RAG.QHelp import DocumentQueryUtils
from rai.RAG.models import QueryCollectionsForm
from rai.assistant.openai_client import generate_embeddings
from rai.internal.chromadb import ChromaClient
from F.LOG import Log

Log = Log("Rai Data Loader")
open_ai_key = os.getenv("OPENAI_API_KEY")


###############################################################################
#                Chroma (Vector-Based) Query Handler                          #
###############################################################################
class VectorStore(ChromaClient, DocumentQueryUtils):
    """
    Contains all functions that perform vector-based (Chroma) queries.
    """
    def __init__(self):
        super().__init__()

    @staticmethod
    def parse_chroma_results(results):
        if results:
            docs = DICT.get("documents", results, [])
            documents = '\n'.join(LIST.flatten(docs))
            return documents
        return None

    @staticmethod
    def get_documents(collection, results) -> List:
        if results:
            docs = DICT.get(collection, results, [])
            return docs
        return None

    @staticmethod
    def find_documents(name, results: dict) -> List:
        if results:
            for item in results.keys():
                if Re.contains(name, item):
                    return VectorStore.get_documents(item, results)
        return None

    def get_all(self, collection):
        results = self.get(collection)
        # Uses the document merging function from DocumentQueryUtils
        return DocumentQueryUtils.merge_sort_all_results(query_results=[results.model_dump()])

    def queryThreaded(self, *collections, user_prompt: str, k: int = 5, where: dict = None):
        query_results = {}

        def query_db(collection, user_prompt, where):
            query_results[collection] = self.querySingleCollection(
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

    def querySingleCollection(self, collection, user_message: str, k: int = 5, where: dict = None):
        try:
            print("User Query:", user_message)
            results = self.base_query_doc_vector(
                collection_name=collection,
                query=user_message,
                embedding_function=generate_embeddings,
                k=k,
                where=where
            )
            # Delegate merging and sorting to the document utility class.
            return DocumentQueryUtils.merge_sort_query_results(query_results=[results.model_dump()], k=k)
        except Exception as e:
            Log.e("Failed to query", e)
            return None

    def queryModelCollection(self, *base_paths, user_message: str, k: int = 5) -> Optional[str]:
        try:
            print("User Query:", user_message)
            results: List[Dict[str, Any]] = self.query_vector_by_chain_name(*base_paths, query=user_message, k=k)
            if results:
                docs: List = DICT.get("documents", results, [])
                documents = '\n'.join(LIST.flatten(docs))
                return documents
            Log.w("No Vectors Found, Reverting to Text Based.")
            results_text = self.query_texts_by_chain_name(*base_paths, query=user_message, k=k)
            if results_text:
                docs: List = DICT.get("documents", results_text, [])
                documents = '\n'.join(LIST.flatten(docs))
                return documents
            return None
        except Exception as e:
            Log.e("Failed to query", e)
            return None

    def query_texts_by_chain_name(self, *base_chain: str, query: str, k: int = 10):
        try:
            collects = LIST.flatten(base_chain)
            Log.i(f"Collections: {collects}")
            return self.query_collection_text(
                collection_names=collects,
                query=query,
                k=k
            )
        except ValueError as e:
            Log.e(f"Validation error: {e}")
            return None
        except Exception as e:
            Log.e("An unexpected error occurred", e)
            return None

    def query_vector_by_chain_name(self, *base_chain: str, query: str, k: int = 10):
        try:
            collects = LIST.flatten(base_chain)
            Log.i(f"Collections: {collects}")
            return self.query_chroma_form(form_data=QueryCollectionsForm(
                collection_names=collects,
                query=query,
                k=k
            ))
        except ValueError as e:
            Log.e(f"Validation error: {e}")
            return None
        except Exception as e:
            Log.e("An unexpected error occurred", e)
            return None

    def query_chroma_form(self, form_data: QueryCollectionsForm):
        try:
            return self.query_collection_vector(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_embeddings,
                k=form_data.k if form_data.k else 3,
            )
        except Exception as e:
            print(e)
            return {}

    def query_collection_vector(self, collection_names: List[str], query: str, embedding_function, k: int) -> Dict[str, List[List[Any]]]:
        results = []
        for collection_name in collection_names:
            if collection_name:
                Log.i(f"Querying [ {collection_name} ]")
                try:
                    result = self.base_query_doc_vector(
                        collection_name=collection_name,
                        query=query,
                        k=k,
                        embedding_function=embedding_function,
                    )
                    results.append(result.model_dump())
                except Exception as e:
                    Log.e(f"Error when querying the collection: {e}")
        return self.merge_and_sort_query_results(results, k=k)

    def query_collection_text(self, collection_names: List[str], query: str, k: int) -> Dict[str, List[List[Any]]]:
        results = []
        for collection_name in collection_names:
            if collection_name:
                Log.i(f"Querying [ {collection_name} ]")
                try:
                    result = self.base_query_doc_texts(
                        collection_name=collection_name,
                        query=query,
                        k=k,
                    )
                    results.append(result.model_dump())
                except Exception as e:
                    Log.e(f"Error when querying the collection: {e}")
        return self.merge_and_sort_query_results(results, k=k)

    def base_query_doc_vector(self, collection_name: str, query: str, embedding_function, k: int, where: dict = None):
        try:
            result = self.search_vector(
                collection_name=collection_name,
                vectors=[embedding_function(query)],
                limit=k,
                where=where,
            )
            print("result", result)
            print(f"query_doc:result {result}")
            return result
        except Exception as e:
            print(e)
            raise e

    def base_query_doc_texts(self, collection_name: str, query: str, k: int):
        try:
            result = self.search_text(
                collection_name=collection_name,
                texts=[query],
                limit=k,
            )
            print("result", result)
            print(f"query_doc:result {result}")
            return result
        except Exception as e:
            print(e)
            raise e


###############################################################################
#                            Example Usage                                    #
###############################################################################
if __name__ == "__main__":
    # Instantiate the Chroma query handler
    chroma_handler = VectorStore()

    # Example: threaded query across several collections.
    results = chroma_handler.queryThreaded(
        "pcsc2025.2.web.pages",
        "pcsc2025.2.web.contacts",
        "pcsc2025.2.web.events",
        "pcsc2025.2.web.context_groups",
        "pcsc2025.2.web.summaries",
        user_prompt="Who is joel person?",
        k=1
    )

    # Find documents related to "events" within the threaded results.
    events = chroma_handler.find_documents("events", results)
    print("Found events:", events)