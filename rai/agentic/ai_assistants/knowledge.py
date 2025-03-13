import time
from datetime import datetime, timedelta
from typing import List, Type, Union

from pydantic import BaseModel

from rai.RAG.models import StoreDocument, GetResult, SearchResult
from rai.agentic.ai_flows.r_flows import register_flow
from F.LOG import Log

from rai.agentic.ai_plugins.assist import rAssistantPlugin
from rai.assistant.openai_client import generate_embeddings
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
            You are a knowledge base document assistant and manager named 'Raiko Knowledge'.
            You retrieve documents, update documents and delete documents accordingly.
        """

    @staticmethod
    def module_name() -> str:
        return "KnowledgeAssistant"

    class KnowledgeResult(BaseModel):
        answer: str
        prefix: str
        documents: List[dict]


    @staticmethod
    def _required_data_model_type() -> Type[BaseModel]:
        return StoreDocument

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
        self.assistant_log(f"Document Manager initialized with prefix: {self.prefix}")

    @staticmethod
    def safe_parse_out(results) -> List[StoreDocument]:
        try:
            return ChromaClient.parse_to_store_documents(results)
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
        self.assistant_log(f"Attempting to retrieve documents.")
        result = self.rStore().get(self.prefix, combined=True)
        if not result:
            self.assistant_error_log("No documents found in the collection.")
            return []
        if limit is not None:
            if limit == 0: limit = 100
            self.assistant_log(f"Returning [ {limit} ] retrieved documents.")
            result = result[:limit]
        self.assistant_log(f"Returning [ {len(result)} ] retrieved documents.")
        return result

    def get_document_by_id(self, doc_id="1") -> List[dict]:
        """Retrieve a single document by its ID."""
        documents = self.browse_documents()
        for doc in documents:
            if doc["id"] == doc_id:
                return [doc]
        self.assistant_log(f"Document with ID '{doc_id}' not found.")
        return []

    def delete_document(self, doc_id: str="1"):
        """Delete a document from the collection based on its ID."""
        self.assistant_log(f"Attempting to delete document with ID: {doc_id}")
        self.rStore().delete(self.prefix, [doc_id])
        self.assistant_log(f"Document with ID '{doc_id}' deleted.")

    def update_document(self, doc_id: str="1", new_text: str="new"):
        """
        Update an existing document with new text, vector, and optionally new metadata.
        Utilizes the upsert operation, so if the document doesn't exist, it will be inserted.
        """
        self.assistant_log(f"Updating document with ID: {doc_id}")
        item = {
            "id": doc_id,
            "text": new_text,
            "vector": self.rAI().embed(new_text),
            "metadata": {'type': 'ai modifications', 'timestamp': time.time() },
        }
        self.rStore().upsert(self.prefix, [item])
        self.assistant_log(f"Document with ID '{doc_id}' updated.")

    def query_documents_by_specific_date(self, query_date: Union[str, datetime]) -> list[StoreDocument]:
        """
        Query documents that were created on a specific date (UTC).
        The `query_date` can be a datetime object or a string in 'YYYY-MM-DD' format.
        This function returns documents whose metadata 'timestamp' falls between the start of that day (inclusive)
        and the start of the next day (exclusive).
        """
        if isinstance(query_date, str):
            query_date = datetime.strptime(query_date, "%Y-%m-%d")
        start_of_day = datetime(query_date.year, query_date.month, query_date.day)
        end_of_day = start_of_day + timedelta(days=1)
        start_ts = int(start_of_day.timestamp())
        end_ts = int(end_of_day.timestamp())
        where_statement = {"$and": [{"timestamp": {"$gte": start_ts}}, {"timestamp": {"$lt": end_ts}}]}
        self.assistant_log(f"Querying documents on {query_date.date()} (timestamps {start_ts} to {end_ts})")
        results = self.rStore().search_vector(self.prefix, vectors=generate_embeddings(""), limit=100, where=where_statement)
        return self.safe_parse_out(results)

    def query_documents_today(self) -> list[StoreDocument]:
        """
        Query documents that were created today (UTC).
        """
        today = datetime.utcnow()
        self.assistant_log(f"Querying documents for today's date: {today.date()}")
        return self.query_documents_by_specific_date(today)

    def query_documents_by_date_range(self, start_date: Union[str, datetime], end_date: Union[str, datetime]) -> list[
        StoreDocument]:
        """
        Query documents that were created within a specified date range (UTC).
        Both `start_date` and `end_date` can be datetime objects or strings in 'YYYY-MM-DD' format.
        The function returns documents whose metadata 'timestamp' falls between the start of `start_date` (inclusive)
        and the start of the day after `end_date` (exclusive).
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_of_day = datetime(start_date.year, start_date.month, start_date.day)
        end_of_day = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
        start_ts = int(start_of_day.timestamp())
        end_ts = int(end_of_day.timestamp())
        where_statement = {"$and": [{"timestamp": {"$gte": start_ts}}, {"timestamp": {"$lt": end_ts}}]}
        self.assistant_log(
            f"Querying documents from {start_of_day.date()} to {end_date.date()} (timestamps {start_ts} to {end_ts})")
        results = self.rStore().search_vector(self.prefix, vectors=generate_embeddings(""), limit=100, where=where_statement)
        return self.safe_parse_out(results)


if __name__ == "__main__":
    results = KnowledgeAssistant.request("rai2025.3", "Show me all documents")
    print(results)
