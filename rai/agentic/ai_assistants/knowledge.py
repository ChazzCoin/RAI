import time
from typing import List, Type

from pydantic import BaseModel

from rai.RAG.models import StoreDocument
from rai.agentic.ai_flows.r_flows import register_flow
from F.LOG import Log

from rai.agentic.ai_plugins.assist import rAssistantPlugin
from rai.internal.chromadb import ChromaClient

Log = Log("KnowledgeFlow")

"""

<public>
"ask" : purely designed to have the AI drive the entire process.

"flow" : a manual configuration that is run.

"request" : 

<private>
"run" :

"""


@register_flow("knowledge")
class KnowledgeAssistant(rAssistantPlugin):
    """
    A Document Manager that extends the ChromaClient to support AI-driven document management.
    It uses a provided 'prefix' to namespace and manage documents within a specific collection.

    List[dict] / Documents
    {
        "id": id_val,
        "document": doc,
        "metadata": meta
    }
    """

    @staticmethod
    def assistant_rules() -> str:
        return """
        
        """

    class KnowledgeResult(BaseModel):
        answer: str
        prefix: str
        documents: List[dict]


    @staticmethod
    def _required_model() -> Type[BaseModel]:
        return KnowledgeAssistant.KnowledgeResult

    assistant = "knowledge"
    sub_collection: str = "pages"

    @classmethod
    def request(cls, prefix:str, user_prompt:str):
        self = cls(prefix=prefix)
        results = self.decide_and_call(user_prompt)
        if type(results) in [list]:
            parsed = self.safe_parse_out(results)
            if len(parsed) > 0: return parsed
        return results

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __init__(self, prefix: str):
        super().__init__()
        self.rStore().init()
        self.prefix = f"{prefix}.{self.sub_collection}"
        Log.s(f"Document Manager initialized with prefix: {self.prefix}")

    @staticmethod
    def safe_parse_out(results: List[dict]) -> List[StoreDocument]:
        try:
            return ChromaClient.parse_dict_to_store_document(results)
        except Exception as e:
            print(e)
            return []

    def get_all_documents(self) -> List[dict]:
        return self.rStore().get(self.prefix, combined=True)

    def browse_documents(self, limit: int = None) -> List[dict]:
        """
        Retrieve and format all documents from the collection into a browsable list.
        Each document is represented as a dictionary with keys: 'id', 'document', 'metadata'.
        """
        result = self.rStore().get(self.prefix, combined=True)
        if not result:
            Log.e("No documents found in the collection.")
            return []

        if limit is not None:
            result = result[:limit]
        return result

    def get_document_by_id(self, doc_id="1") -> List[dict]:
        """Retrieve a single document by its ID."""
        documents = self.browse_documents()
        for doc in documents:
            if doc["id"] == doc_id:
                return [doc]
        Log.w(f"Document with ID '{doc_id}' not found.")
        return []

    def delete_document(self, doc_id: str="1"):
        """Delete a document from the collection based on its ID."""
        Log.s(f"Attempting to delete document with ID: {doc_id}")
        self.rStore().delete(self.prefix, [doc_id])
        Log.s(f"Document with ID '{doc_id}' deleted.")

    def update_document(self, doc_id: str="1", new_text: str="new"):
        """
        Update an existing document with new text, vector, and optionally new metadata.
        Utilizes the upsert operation, so if the document doesn't exist, it will be inserted.
        """
        Log.s(f"Updating document with ID: {doc_id}")
        item = {
            "id": doc_id,
            "text": new_text,
            "vector": self.rAI().embed(new_text),
            "metadata": {'type': 'ai modifications', 'timestamp': time.time() },
        }
        self.rStore().upsert(self.prefix, [item])
        Log.s(f"Document with ID '{doc_id}' updated.")


if __name__ == "__main__":
    results = KnowledgeAssistant.request("rai2025.1", "Show me the last 10 documents.")
    print(results)
