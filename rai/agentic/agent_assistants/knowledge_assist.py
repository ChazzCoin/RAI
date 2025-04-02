import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Type
from rai.RAG.models import StoreDocument
from rai.agentic.agent_modules.engine import ToolEngine, register_tool_engine
from rai.agentic.agent_modules.result import ToolResult


@register_tool_engine('knowledge-base')
class KnowledgeTool(ToolEngine):

    @staticmethod
    def tool_assistant_name() -> str:
        return "QueryTool"
    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You understand users natural language and convert it into a function or where query for specific page documents.
            Prefix is a users/organizations collection prefix name for routing to their documents.
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
            self.get_tool('set_prefix')
            # self.get_tool('add_page'),
            # self.get_tool('update_page'),
            # self.get_tool('delete_page')
        ]

    async def get_current_state(self) -> ToolResult:
        return self._tool_result

    def query_all(self, query: str, k: int = 5) -> Dict[str, List[StoreDocument]]:
        try:
            wrapped_results: Dict[str, List[StoreDocument]] = self.rStore().queries_store(
                *self.rStore().get_available_sub_collections(self.tool_plan.prefix),
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

    def set_prefix(self, prefix: str) -> ToolResult:
        self.tool_plan.prefix = prefix
        return ToolResult(
            output=f"I have changed the prefix to: [ {prefix} ]",
            success=True
        )
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
            self.rStore().upsert(f"{self.tool_plan.prefix}.pages", [item])
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
            self.rStore().delete(f"{self.tool_plan.prefix}.pages", [doc_id])
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
            self.rStore().upsert(f"{self.tool_plan.prefix}.pages", [item])
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
                collection=f"{self.tool_plan.prefix}.pages",
                user_message=text_query
            )
            return self.attach_data_and_send_result(temp)
        except Exception as e:
            return ToolResult(
                output=f"Something went wrong trying to search. {e}",
                success=False
            )
    def get_all_pages(self, **kwargs) -> ToolResult:
        return self.attach_data_and_send_result(self.get(collection=f"{self.tool_plan.prefix}.pages"))
    def get_latest_page(self, **kwargs) -> ToolResult:
        return self.attach_data_and_send_result(self.get(collection=f"{self.tool_plan.prefix}.pages", where=self.where_is_today()))
    def get_pages_on_date(self, date_query: str) -> ToolResult:
        query_date = datetime.strptime(date_query, "%Y-%m-%d")
        date_time = datetime(query_date.year, query_date.month, query_date.day)
        date_time_plus_one = date_time + timedelta(days=1)
        return self.attach_data_and_send_result(self.get(collection=f"{self.tool_plan.prefix}.pages", where=self.where_between_dates(date_time, date_time_plus_one)))
    def get_pages_between_dates(self, start_date: str, end_date: str) -> ToolResult:
        query_date_start = self.parse_date_query(start_date)
        query_date_end = self.parse_date_query(end_date)
        return self.attach_data_and_send_result(self.get(collection=f"{self.tool_plan.prefix}.pages", where=self.where_between_dates(query_date_start, query_date_end)))
    def get_pages_where(self, where: dict) -> List[StoreDocument]:
        return self.get(collection=f"{self.tool_plan.prefix}.pages", where=where)



if __name__ == "__main__":
    looper = asyncio.get_event_loop()
    looper.run_until_complete(KnowledgeTool.go(request="My collection prefix is 'general2025.1.memory'. Show me all my documents please."))
