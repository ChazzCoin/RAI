import logging, uuid, os, requests
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

from rai.internal.connectors import VECTOR_DB_CLIENT
from rai.utils.misc import get_last_user_message
from rai.env import SRC_LOG_LEVELS
from typing import Any
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever

import operator
from typing import Optional, Sequence

from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])
from F.LOG import Log
Log = Log("Rai.utils")

class VectorSearchRetriever(BaseRetriever):
    collection_name: Any
    embedding_function: Any
    top_k: int

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        result = VECTOR_DB_CLIENT.search_vector(
            collection_name=self.collection_name,
            vectors=[self.embedding_function(query)],
            limit=self.top_k,
        )

        ids = result.ids[0]
        metadatas = result.metadatas[0]
        documents = result.documents[0]

        results = []
        for idx in range(len(ids)):
            results.append(
                Document(
                    metadata=metadatas[idx],
                    page_content=documents[idx],
                )
            )
        return results


def query_doc_with_hybrid_search(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
) -> dict:
    try:
        result = VECTOR_DB_CLIENT.get(collection_name=collection_name)

        bm25_retriever = BM25Retriever.from_texts(
            texts=result.documents[0],
            metadatas=result.metadatas[0],
        )
        bm25_retriever.k = k

        vector_search_retriever = VectorSearchRetriever(
            collection_name=collection_name,
            embedding_function=embedding_function,
            top_k=k,
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_search_retriever], weights=[0.5, 0.5]
        )
        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)
        result = {
            "distances": [[d.metadata.get("score") for d in result]],
            "documents": [[d.page_content for d in result]],
            "metadatas": [[d.metadata for d in result]],
        }

        Log.i(f"query_doc_with_hybrid_search:result {result}")
        return result
    except Exception as e:
        Log.e(e)
        raise e





# def query_collection_with_hybrid_search(
#     collection_names: list[str],
#     query: str,
#     embedding_function,
#     k: int,
#     reranking_function,
#     r: float,
# ) -> dict[str, list[list[Any]]]:
#     results = []
#     error = False
#     for collection_name in collection_names:
#         try:
#             result = query_doc_with_hybrid_search(
#                 collection_name=collection_name,
#                 query=query,
#                 embedding_function=embedding_function,
#                 k=k,
#                 reranking_function=reranking_function,
#                 r=r,
#             )
#             results.append(result)
#         except Exception as e:
#             log.exception(
#                 "Error when querying the collection with " f"hybrid_search: {e}"
#             )
#             error = True
#
#     if error:
#         print(
#             "Hybrid search failed for all collections. Using Non hybrid search as fallback."
#         )
#         results = VECTOR_DB_CLIENT.query_collection_vector(
#             collection_names=collection_names,
#             query=query,
#             embedding_function=embedding_function,
#             k=3
#         )
#     return VECTOR_DB_CLIENT.merge_and_sort_query_results(results, k=k, reverse=True)

#
# def rag_template(template: str, context: str, query: str):
#     count = template.count("[context]")
#     assert "[context]" in template, "RAG template does not contain '[context]'"
#
#     if "<context>" in context and "</context>" in context:
#         log.debug(
#             "WARNING: Potential prompt injection attack: the RAG "
#             "context contains '<context>' and '</context>'. This might be "
#             "nothing, or the user might be trying to hack something."
#         )
#
#     if "[query]" in context:
#         query_placeholder = f"[query-{str(uuid.uuid4())}]"
#         template = template.replace("[query]", query_placeholder)
#         template = template.replace("[context]", context)
#         template = template.replace(query_placeholder, query)
#     else:
#         template = template.replace("[context]", context)
#         template = template.replace("[query]", query)
#     return template



#
# def get_rag_context(
#     files,
#     messages,
#     embedding_function,
#     k,
#     reranking_function,
#     r,
#     hybrid_search,
# ):
#     log.debug(f"files: {files} {messages} {embedding_function} {reranking_function}")
#     query = get_last_user_message(messages)
#
#     extracted_collections = []
#     relevant_contexts = []
#
#     for file in files:
#         context = None
#
#         collection_names = (
#             file["collection_names"]
#             if file["type"] == "collection"
#             else [file["collection_name"]] if file["collection_name"] else []
#         )
#
#         collection_names = set(collection_names).difference(extracted_collections)
#         if not collection_names:
#             log.debug(f"skipping {file} as it has already been extracted")
#             continue
#
#         try:
#             context = None
#             if file["type"] == "text":
#                 context = file["content"]
#             else:
#                 if hybrid_search:
#                     try:
#                         context = query_collection_with_hybrid_search(
#                             collection_names=collection_names,
#                             query=query,
#                             embedding_function=embedding_function,
#                             k=k,
#                             reranking_function=reranking_function,
#                             r=r,
#                         )
#                     except Exception as e:
#                         log.debug(
#                             "Error when using hybrid search, using"
#                             " non hybrid search as fallback."
#                         )
#
#                 if (not hybrid_search) or (context is None):
#                     context = VECTOR_DB_CLIENT.query_collection_vector(
#                         collection_names=collection_names,
#                         query=query,
#                         embedding_function=embedding_function,
#                         k=k,
#                     )
#         except Exception as e:
#             log.exception(e)
#
#         if context:
#             relevant_contexts.append({**context, "source": file})
#
#         extracted_collections.extend(collection_names)
#
#     contexts = []
#     citations = []
#
#     for context in relevant_contexts:
#         try:
#             if "documents" in context:
#                 contexts.append(
#                     "\n\n".join(
#                         [text for text in context["documents"][0] if text is not None]
#                     )
#                 )
#
#                 if "metadatas" in context:
#                     citations.append(
#                         {
#                             "source": context["source"],
#                             "document": context["documents"][0],
#                             "metadata": context["metadatas"][0],
#                         }
#                     )
#         except Exception as e:
#             log.exception(e)
#
#     return contexts, citations



def generate_openai_batch_embeddings(
    model: str, texts: list[str], key: str, url: str = "https://api.openai.com/v1"
) -> Optional[list[list[float]]]:
    try:
        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={"input": texts, "model": model},
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        print(e)
        return None

class RerankCompressor(BaseDocumentCompressor):
    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = "forbid"
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        reranking = self.reranking_function is not None

        if reranking:
            scores = self.reranking_function.predict(
                [(query, doc.page_content) for doc in documents]
            )
        else:
            from sentence_transformers import util

            query_embedding = self.embedding_function(query)
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents]
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        docs_with_scores = list(zip(documents, scores.tolist()))
        if self.r_score:
            docs_with_scores = [
                (d, s) for d, s in docs_with_scores if s >= self.r_score
            ]

        result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
        final_results = []
        for doc, doc_score in result[: self.top_n]:
            metadata = doc.metadata
            metadata["score"] = doc_score
            doc = Document(
                page_content=doc.page_content,
                metadata=metadata,
            )
            final_results.append(doc)
        return final_results
