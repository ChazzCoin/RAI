import os
from typing import Optional
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from F import DICT, LIST
from typing_extensions import Any
from rai.RAG.models import QueryCollectionsForm
from rai.assistant.openai_client import generate_embeddings
from rai.internal.chromadb import ChromaClient
from F.LOG import Log
Log = Log("Rai Data Loader")

open_ai_key = os.getenv("OPENAI_API_KEY")

class Q(ChromaClient):
    llm = None

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
            results: [{str: []}] = self.query_vector_by_chain_name(*base_paths, query=user_message, k=k)
            if results:
                docs: [] = DICT.get("documents", results, [])
                documents = '\n'.join(LIST.flatten(docs))
                return documents
            Log.w("No Vectors Found, Reverting to Text Based.")
            results_text = self.query_texts_by_chain_name(*base_paths, query=user_message, k=k)
            if results_text:
                docs: [] = DICT.get("documents", results_text, [])
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
    """ 2 """
    def query_vector_by_chain_name(self, *base_chain: str, query: str, k: int = 10):
        try:
            collects = LIST.flatten(base_chain)
            Log.i(f"Collections: {collects}")
            return self.query_chroma_form(
                form_data=QueryCollectionsForm(
                    collection_names=collects,
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
            return self.query_collection_vector(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_embeddings,
                k=form_data.k if form_data.k else 3,
            )
        except Exception as e:
            print(e)
            return {}

    def query_collection_vector(self, collection_names: list[str], query: str, embedding_function, k: int) -> dict[str, list[list[Any]]]:
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
            else:
                pass
        return self.merge_and_sort_query_results(results, k=k)
    def query_collection_text(self, collection_names: list[str], query: str, k: int) -> dict[str, list[list[Any]]]:
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
            else:
                pass
        return self.merge_and_sort_query_results(results, k=k)

    def base_query_doc_vector(self, collection_name: str, query: str, embedding_function, k: int):
        try:
            result = self.search_vector(
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

    # Query Refinement Function
    def refine_query(self, user_query: str) -> str:
        """
        Refines the user query for better search relevance.
        :param user_query: Original user query.
        :return: Refined query.
        """
        query_refinement_prompt = PromptTemplate(
            input_variables=["query"],
            template="You are a helpful assistant improving user search queries. "
                     "Original query: {query}\n"
                     "Refined query: Make it clearer, more specific, and suitable for retrieval."
        )

        query_chain = LLMChain(llm=self.llm, prompt=query_refinement_prompt)
        refined_query = query_chain.run(query=user_query)
        return refined_query.strip()

    # Context Condensation Function
    def condense_context(self, retrieved_chunks) -> str:
        """
        Condenses retrieved document chunks into a concise summary.
        :param retrieved_chunks: List of retrieved document chunks.
        :return: Condensed summary of the context.
        """
        combined_context = ""
        if type(retrieved_chunks) in [list, tuple]:
            combined_context = "\n".join(retrieved_chunks)
        elif type(retrieved_chunks) in [str]:
            combined_context = retrieved_chunks
        context_summary_prompt = PromptTemplate(
            input_variables=["context"],
            template="You are an assistant summarizing information for relevance. "
                     "Here is the context:\n{context}\n\n"
                     "Summarize the key points clearly and concisely."
        )

        summarization_chain = LLMChain(llm=self.llm, prompt=context_summary_prompt)
        condensed_summary = summarization_chain.run(context=combined_context)
        return condensed_summary.strip()