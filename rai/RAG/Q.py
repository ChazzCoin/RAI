from typing import Optional

from F import DICT, LIST
from typing_extensions import Any
from rai.RAG.models import QueryCollectionsForm
from rai.assistant.openai_client import generate_embeddings
from rai.internal.chromadb import ChromaClient
from F.LOG import Log
Log = Log("Rai Data Loader")


class Q(ChromaClient):

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse_chroma_results(results):
        if results:
            docs: [] = DICT.get("documents", results, [])
            documents = '\n'.join(LIST.flatten(docs))
            return documents
        return None

    def queryModelCollection(self, *base_paths, user_message: str, k: int = 5) -> Optional[str]:
        try:
            print("User Query:", user_message)
            results: [{str: []}] = self.query_chroma_by_prefix(*base_paths, query=user_message, k=k)
            if results:
                docs: [] = DICT.get("documents", results, [])
                documents = '\n'.join(LIST.flatten(docs))
                return documents
            Log.i("Returning custom SYS Prompt.")
            return None
        except Exception as e:
            Log.e("Failed to query", e)
            return None

    """ MAIN QUERY FUNCTION!! """
    def query_chroma_by_prefix(self, *base_chain:str, query: str, k: int = 10):
        try:
            user_collections = self.get_all_collections_by_chain(*base_chain)
            Log.i(f"Collections: {user_collections}")
            return self.query_chroma_form(
                form_data=QueryCollectionsForm(
                    collection_names=user_collections,
                    query=query,
                    k=k
                )
            )
        except ValueError as e:
            Log.e(f"Validation error: {e}")
            return None
        except Exception as e:
            Log.e("An unexpected error occurred", e)
            return None

    def query_chroma_form(self, form_data: QueryCollectionsForm):
        try:
            return self.query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_embeddings,
                k=form_data.k if form_data.k else 3,
            )
        except Exception as e:
            print(e)
            return {}

    def query_collection(self, collection_names: list[str], query: str, embedding_function, k: int) -> dict[str, list[list[Any]]]:
        results = []
        for collection_name in collection_names:
            if collection_name:
                Log.i(f"Querying [ {collection_name} ]")
                try:
                    result = self.query_doc(
                        collection_name=collection_name,
                        query=query,
                        k=k,
                        embedding_function=embedding_function,
                    )
                    results.append(result.model_dump())
                except Exception as e:
                    Log.e(f"Error when querying the collection: {e}")
            else:
                pass
        return self.merge_and_sort_query_results(results, k=k)

    def query_doc(self, collection_name: str, query: str, embedding_function, k: int):
        try:
            result = self.search(
                collection_name=collection_name,
                vectors=[embedding_function(query)],
                limit=k,
            )
            print("result", result)
            print(f"query_doc:result {result}")
            return result
        except Exception as e:
            print(e)
            raise e

    @staticmethod
    def merge_and_sort_query_results(query_results: list[dict], k: int, reverse: bool = False) -> dict[str, list[list[Any]]]:
        # Initialize lists to store combined data
        combined_distances = []
        combined_documents = []
        combined_metadatas = []

        for data in query_results:
            combined_distances.extend(data["distances"][0])
            combined_documents.extend(data["documents"][0])
            combined_metadatas.extend(data["metadatas"][0])

        # Create a list of tuples (distance, document, metadata)
        combined = list(zip(combined_distances, combined_documents, combined_metadatas))

        # Sort the list based on distances
        combined.sort(key=lambda x: x[0], reverse=reverse)

        # We don't have anything :-(
        if not combined:
            sorted_distances = []
            sorted_documents = []
            sorted_metadatas = []
        else:
            # Unzip the sorted list
            sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)

            # Slicing the lists to include only k elements
            sorted_distances = list(sorted_distances)[:k]
            sorted_documents = list(sorted_documents)[:k]
            sorted_metadatas = list(sorted_metadatas)[:k]

        # Create the output dictionary
        result = {
            "distances": [sorted_distances],
            "documents": [sorted_documents],
            "metadatas": [sorted_metadatas],
        }

        return result