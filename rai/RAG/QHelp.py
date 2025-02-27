import os
import threading
import uuid
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
            distances = result.get("distances" or "score", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            for dist, doc, meta in zip(distances, documents, metadatas):
                combined_entries.append({
                    "id": str(uuid.uuid4()),
                    "distance": dist,
                    "document": doc,
                    "metadata": meta,
                    "formatted": f"DOCUMENT:\n{doc}\nMETADATA:\n{str(meta)}"
                })
        combined_entries.sort(key=lambda x: x["distance" or "score"], reverse=reverse)
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






