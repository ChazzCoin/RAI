import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union, Type
from rai.RAG.models import StoreDocument
from rai.agentic.agent_tools.engine import ToolEngine
from rai.agentic.agent_tools.result import ToolResult

class QueryModule:
    @staticmethod
    def parse_date_query(date_query: str) -> datetime:
        qd = datetime.strptime(date_query, "%Y-%m-%d")
        return datetime(qd.year, qd.month, qd.day)
    @staticmethod
    def where_id_equals(idx: str):
        return QueryModule.where_key_equals(key='id', value=idx)
    @staticmethod
    def where_key_equals(key, value):
        return {key: {"$eq": value}}
    @staticmethod
    def where_key_is_gte(key, value):
        return {key: {"$gte": value}}
    @staticmethod
    def where_key_is_lte(key, value):
        return {key: {"$lte": value}}
    @staticmethod
    def _get_date(query_date: Union[str, datetime]):
        if isinstance(query_date, str):
            query_date = datetime.strptime(query_date, "%Y-%m-%d")
        return datetime(query_date.year, query_date.month, query_date.day)
    @staticmethod
    def _get_date_now():
        return int(datetime.now().timestamp())
    @staticmethod
    def _get_date_tomorrow():
        return int((datetime.now() + timedelta(days=1)).timestamp())
    @staticmethod
    def _get_date_yesterday():
        return int((datetime.now() - timedelta(days=1)).timestamp())
    @staticmethod
    def _get_date_x_days_in_future(x: int):
        return int((datetime.now() + timedelta(days=x)).timestamp())
    @staticmethod
    def _get_date_x_days_ago(x: int):
        return int((datetime.now() - timedelta(days=x)).timestamp())
    @staticmethod
    def where_is_today():
        return {"$and": [{"timestamp": {"$gte": QueryModule._get_date_now()}},
                         {"timestamp": {"$lt": QueryModule._get_date_tomorrow()}}]}
    @staticmethod
    def where_between_dates(start: datetime, end: datetime):
        return {"$and": [{"timestamp": {"$gte": start}}, {"timestamp": {"$lt": end}}]}
    @staticmethod
    def where_parent_id(parent_id):
        return {"parent_id": {"$eq": parent_id}}
    @staticmethod
    def where_page_id(page_id):
        return {"page_id": {"$eq": page_id}}
    @staticmethod
    def where_page_number(page_number):
        return {"page_number": {"$eq": page_number}}
    @staticmethod
    def remove_text_before_last_period(text: str) -> str:
        if '.' not in text: return text
        return text.rsplit('.', 1)[-1]
    @staticmethod
    def filter_by_distance(objects: list[dict]) -> list[dict]:
        if not objects: return []
        # Sort the list by 'distance' in ascending order
        objects.sort(key=lambda x: x['distance'])
        # Get the top object's distance
        top_distance = objects[0]['distance']
        # Define the valid range
        min_distance = top_distance - 0.25
        max_distance = top_distance + 0.25
        # Filter objects within the valid range
        filtered_objects = [obj for obj in objects if min_distance <= obj['distance'] <= max_distance]
        return filtered_objects
    @staticmethod
    def real_time_data():
        now = datetime.now()
        return f""" Current Date & Time: {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")} """
    @staticmethod
    def sort_documents(documents: List[Dict[str, Any]]) -> Dict[str, Dict[int, Dict[str, Any]]]:
        sorted_by_brief = defaultdict(list)
        # Group documents by brief_id
        for doc in documents:
            brief_id = doc['metadata']['brief_id']
            sorted_by_brief[brief_id].append(doc)
        # Sort each brief_id group by page_index
        result = {}
        for brief_id, docs in sorted_by_brief.items():
            sorted_docs = sorted(docs, key=lambda d: d['metadata']['page_index'])
            # Map sorted docs by page_index
            result[brief_id] = {doc['metadata']['page_index']: doc for doc in sorted_docs}
        return result


class QueryTool(ToolEngine, QueryModule):

    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix
    @staticmethod
    def tool_assistant_name() -> str:
        return "QueryTool"
    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You understand users natural language and convert it into a function or where query for specific page documents.
        """
    @staticmethod
    def module_name() -> str:
        return "QueryTool"
    def _required_data_model_type(self) -> Type[StoreDocument]:
        """Return the required data model for the assistant."""
        return StoreDocument

    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool('get_pages'),
            self.get_tool('get_latest_page'),
            self.get_tool('get_pages_on_date'),
            self.get_tool('get_pages_between_dates'),
            self.get_tool('search'),
            self.get_tool('add_page'),
            self.get_tool('update_page'),
            self.get_tool('delete_page')
        ]

    async def get_current_state(self) -> ToolResult:
        return self._tool_result
    @staticmethod
    def attach_data_and_send_result(results) -> ToolResult:
        return ToolResult(
            output="We have attached the query document results to the holder.",
            success=True,
            holding="StoreDocument",
            holder=results
        )

    def query_all(self, query: str, k: int = 5) -> Dict[str, List[StoreDocument]]:
        try:
            wrapped_results: Dict[str, List[StoreDocument]] = self.rStore().queries_store(
                *self.rStore().get_available_sub_collections(self.prefix),
                user_prompt=query,
                k=k
            )
            return wrapped_results
        except Exception as e:
            print(f"Error: {e}")
            return {}
    def get(self, collection: str, limit: int = 100, offset: int = 0, where: dict = None) -> List[StoreDocument]:
        try:
            return self.rStore().get_all_from_store(
                collection=collection,
                limit=limit,
                offset=offset,
                where=where
            )
        except Exception as e:
            print(e)
            return []

    def add_page(self, raw_text: str, metadata: dict = None) -> ToolResult:
        """
        Add a new document to the collection with provided raw text and optional metadata.
        """
        try:
            doc_id = str(uuid.uuid4())
            self.log_voice(f"Adding a new document with id [ {doc_id} ]")
            item = {
                "id": doc_id,
                "text": raw_text,
                "vector": self.llm().embed(raw_text),
                "metadata": metadata if metadata else {'type': 'user entry', 'timestamp': self._get_date_now()},
            }
            self.rStore().upsert(f"{self.prefix}.pages", [item])
            self.log_voice(f"New document added with ID '{doc_id}'.")
            return ToolResult(
                output=f"New document added with ID '{doc_id}'.",
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong adding the document. {e}",
                success=False
            )
    def delete_page(self, doc_id: str) -> ToolResult:
        """Delete a document from the collection based on its ID."""
        try:
            self.log_voice(f"Attempting to delete document with ID: {doc_id}")
            self.rStore().delete(f"{self.prefix}.pages", [doc_id])
            self.log_voice(f"Document with ID '{doc_id}' deleted.")
            return ToolResult(
                output=f"Document with ID '{doc_id}' deleted.",
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong. {e}",
                success=False
            )
    def update_page(self, doc_id: str, new_text: str) -> ToolResult:
        """
        Update an existing document with new text, vector, and optionally new metadata.
        Utilizes the upsert operation, so if the document doesn't exist, it will be inserted.
        """
        self.log_voice(f"Updating document with ID: {doc_id}")
        try:
            item = {
                "id": doc_id,
                "text": new_text,
                "vector": self.llm().embed(new_text),
                "metadata": {'type': 'ai modifications', 'timestamp': self._get_date_now() },
            }
            self.rStore().upsert(f"{self.prefix}.pages", [item])
            self.log_voice(f"Document with ID '{doc_id}' updated.")
            return ToolResult(
                output=f"Document with ID '{doc_id}' updated.",
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong. {e}",
                success=False
            )
    def search(self, text_query: str) -> ToolResult:
        try:
            temp = self.rStore().query_store(
                collection=f"{self.prefix}.pages",
                user_message=text_query
            )
            return self.attach_data_and_send_result(temp)
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong trying to search. {e}",
                success=False
            )
    def get_pages(self) -> ToolResult:
        return self.attach_data_and_send_result(self.get(collection=f"{self.prefix}.pages"))
    def get_latest_page(self) -> ToolResult:
        return self.attach_data_and_send_result(self.get(collection=f"{self.prefix}.pages", where=self.where_is_today()))
    def get_pages_on_date(self, date_query: str) -> ToolResult:
        query_date = datetime.strptime(date_query, "%Y-%m-%d")
        date_time = datetime(query_date.year, query_date.month, query_date.day)
        date_time_plus_one = date_time + timedelta(days=1)
        return self.attach_data_and_send_result(self.get(collection=f"{self.prefix}.pages", where=self.where_between_dates(date_time, date_time_plus_one)))
    def get_pages_between_dates(self, start_date: str, end_date: str) -> ToolResult:
        query_date_start = self.parse_date_query(start_date)
        query_date_end = self.parse_date_query(end_date)
        return self.attach_data_and_send_result(self.get(collection=f"{self.prefix}.pages", where=self.where_between_dates(query_date_start, query_date_end)))

    def get_pages_where(self, where: dict) -> List[StoreDocument]:
        return self.get(collection=f"{self.prefix}.pages", where=where)



if __name__ == "__main__":
    looper = asyncio.get_event_loop()
    looper.run_until_complete(QueryTool(prefix="referral2025.1").ask(request="Which documents are Electronically signed by Kasmia,Abdei H, MD?"))
