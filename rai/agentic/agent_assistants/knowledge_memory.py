import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Type

from F import LIST

from rai.RAG.models import StoreDocument
from rai.agentic.agent_tools.engine import ToolEngine, register_tool_engine
from rai.agentic.agent_tools.result import ToolResult


@register_tool_engine('memory-assistant')
class MemoryTool(ToolEngine):

    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix
    @staticmethod
    def tool_assistant_name() -> str:
        return "MemoryTool"
    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You manage and save documents as 'memories' for long term storage and then retrieve them upon command.
            **DO NOT ADD, UPDATE, DELETE OR MODIFY ANY DATA WITHOUT THE USERS DIRECTION FIRST**
            **LESS STEPS, THE BETTER FOR ME**
            MEMORIES == DOCUMENTS
            MEMORY == DOCUMENT
        """
    @staticmethod
    def module_name() -> str:
        return "LongTermMemoryTool"
    def _required_data_model_type(self) -> Type[StoreDocument]:
        """Return the required data model for the assistant."""
        return StoreDocument

    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool('search_memory'),
            self.get_tool('save_memory'),
            self.get_tool('retrieve_all_memories'),
            self.get_tool('finish'),
        ]

    async def get_current_state(self) -> ToolResult:
        return self._tool_result
    @staticmethod
    def attach_data_and_send_result(results) -> ToolResult:
        return ToolResult(
            output="We have attached the memories to the holder.",
            success=True,
            holding="StoreDocument",
            holder=results
        )
    def key(self) -> str: return f"memory.{self.prefix}"

    def finish(self):
        self.quit()
        return self.finish_and_then_respond()
    def search_memory(self, user_prompt: str) -> ToolResult:
        """ """
        try:
            return self.attach_data_and_send_result(self.rStore().query_store(
                collection=self.key(),
                user_message=user_prompt,
                limit=5,
                combined=True
            ))
        except Exception as e:
            return ToolResult(
                output=str(e),
                success=False
            )
    def save_memory(self, memory_data:str) -> ToolResult:
        """ SAVE a General Memory """
        try:
            interaction_text = f"Memory: {memory_data}"
            context_prompt = self.llm().tool('summarize', user_prompt=interaction_text)
            interaction_text = interaction_text + f"\nSummarized Context: {context_prompt}"
            interaction_id = str(uuid.uuid4())
            meta = {"prefix": self.prefix, "timestamp": int(time.time()), "type": "long" }
            self.rStore().create_and_store(self.key(), id=interaction_id, text=interaction_text, metadata=meta)
            self.log_voice(f"Stored interaction {interaction_id} for session {self.prefix}.")
            return ToolResult(
                output=interaction_text,
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"An error occurred while saving the interaction. {e}",
                success=False
            )
    def retrieve_all_memories(self) -> ToolResult:
        """ """
        try:
            results = self.rStore().get_all_from_store(self.key())
            return ToolResult(
                output="I have retrieved the interaction from the memory.",
                holding="StoreDocument",
                holder=results,
                success=True
            )
        except Exception as e:
            return ToolResult(
                output=f"An error occurred while retrieving the interaction. {e}",
                success=False
            )

    # def retrieve_last_memory(self) -> ToolResult:
    #     """ """
    #     results = self.rStore().get_all(self.key())
    #     if not results:
    #         return "No previous interactions found."
    #     last_interaction = sorted(
    #         results,
    #         key=lambda doc: doc.get("metadata", {}).get("timestamp", 0),
    #         reverse=True
    #     )[0]
    #     return last_interaction.get("document", "No document content found.")
if __name__ == "__main__":
    looper = asyncio.get_event_loop()
    looper.run_until_complete(MemoryTool(prefix="referral2025.2").ask(request="Show me all my memories"))
