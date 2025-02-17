import os
import threading
from typing import Optional, List, Dict, Any

from F import DICT, LIST
from typing_extensions import Any  # noqa: F401
from F.LOG import Log

Log = Log("Rai Data Loader")
open_ai_key = os.getenv("OPENAI_API_KEY")


###############################################################################
#             Document-Based Functions & Re-Ranking Utilities                 #
###############################################################################
class DocumentQueryUtils:


    @staticmethod
    def unwrap_results(results: dict) -> List:
        unwrapped_results = []
        for k, v in results.items():
            if not v:
                continue
            unwrapped_results.append(v)
        flat = LIST.flatten(unwrapped_results)
        sort_flat = sorted(flat, key=lambda x: x["distance"])
        return sort_flat

    @staticmethod
    def unwrap_formatted(results, k=5):
        unwrapped_results = []
        for i in results:
            formatted = DICT.get("formatted", i, "")
            unwrapped_results.append(formatted)
        if len(unwrapped_results) <= k:
            return "\nDOCUMENT\n".join(unwrapped_results)
        else:
            return "\nDOCUMENT\n".join(unwrapped_results[:k])

    @staticmethod
    def merge_sort_query_results(query_results: List[Dict[str, List[List[Any]]]], k: int, reverse: bool = False) -> \
    List[Dict[str, Any]]:
        combined_entries: List[Dict[str, Any]] = []
        for result in query_results:
            distances = result.get("distances", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            for dist, doc, meta in zip(distances, documents, metadatas):
                combined_entries.append({
                    "distance": dist,
                    "document": doc,
                    "metadata": meta,
                    "formatted": f"DOCUMENT:\n{doc}\nMETADATA:\n{str(meta)}"
                })
        combined_entries.sort(key=lambda x: x["distance"], reverse=reverse)
        top_results = combined_entries[:k]
        return top_results

    @staticmethod
    def merge_sort_all_results(query_results: List[Dict[str, List[List[Any]]]]) -> List[Dict[str, Any]]:
        combined_entries: List[Dict[str, Any]] = []
        for result in query_results:
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            for doc, meta in zip(documents, metadatas):
                combined_entries.append({
                    "document": doc,
                    "metadata": meta,
                    "formatted": f"DOCUMENT:\n{doc}\nMETADATA:\n{str(meta)}"
                })
        return combined_entries

    @staticmethod
    def merge_and_sort_query_results(query_results: List[dict], k: int, reverse: bool = False) -> Dict[
        str, List[List[Any]]]:
        combined_distances = []
        combined_documents = []
        combined_metadatas = []
        for data in query_results:
            combined_distances.extend(data["distances"][0])
            combined_documents.extend(data["documents"][0])
            combined_metadatas.extend(data["metadatas"][0])
        combined = list(zip(combined_distances, combined_documents, combined_metadatas))
        combined.sort(key=lambda x: x[0], reverse=reverse)
        if not combined:
            sorted_distances = []
            sorted_documents = []
            sorted_metadatas = []
        else:
            sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)
            sorted_distances = list(sorted_distances)[:k]
            sorted_documents = list(sorted_documents)[:k]
            sorted_metadatas = list(sorted_metadatas)[:k]
        result = {
            "distances": [sorted_distances],
            "documents": [sorted_documents],
            "metadatas": [sorted_metadatas],
        }
        return result





