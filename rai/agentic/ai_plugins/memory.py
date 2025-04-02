import datetime
import time
import uuid
from typing import List, Optional

from F import LIST

from rai.RAG.models import StoreDocument
from rai.agentic.ai_modules.query import QueryModule
from rai.agentic.ai_modules.r import rModule


class MemoryTool(rModule, QueryModule):
    @staticmethod
    def module_name() -> str: return "memory"
    prefix: str = 'general2025.1'
    memories: List[StoreDocument] = []
    @property
    def memory_list(self) -> List[str]: return [item.document for item in self.memories]
    def key(self) -> str: return f"{self.prefix}.memory"
    def set_prefix(self, prefix:str): self.prefix = prefix
    def search_memory(self, user_prompt: str, to_str:bool=True) -> List[StoreDocument] | List[str]:
        """ """
        try:
            items = self.rStore().query_store(
                collection=self.key(),
                user_message=user_prompt,
                k=5
            )
            if to_str: return [item.document for item in items]
            return items
        except Exception as e:
            print(e)
            return []
    def save_memory(self, memory_data:str, summarize:bool=False) -> Optional[str]:
        """ SAVE a General Memory """
        try:
            interaction_text = f"Memory: {memory_data}"
            if summarize:
                context_prompt = self.llm().tool('summarize', user_prompt=interaction_text)
                interaction_text = interaction_text + f"\nSummarized Context: {context_prompt}"
            interaction_id = str(uuid.uuid4())
            meta = {"prefix": self.prefix, "timestamp": int(datetime.datetime.utcnow().timestamp()), "type": "long" }
            self.rStore().create_and_store(self.key(), id=interaction_id, text=interaction_text, metadata=meta)
            print(f"Stored interaction {interaction_id} for session {self.prefix}.")
            return interaction_id
        except Exception as e:
            print(e)
            return None
    def retrieve_all_memories(self, to_str:bool=True) -> List[StoreDocument] | List[str]:
        try:
            items = self.rStore().get_all_from_store(self.key())
            if to_str: return [item.document for item in items]
            return items
        except Exception as e:
            print(e)
            return []
    def retrieve_last_memory(self, to_str:bool=True) -> StoreDocument | str | None:
        item = self.get(collection=self.key(), limit=1, where=self.where_is_today())
        if item:
            if type(item) in [list, tuple]:
                doc = LIST.get(0, item, None)
                if doc and to_str: return doc.document
                return doc
            elif isinstance(item, StoreDocument):
                if to_str: return item.document
                return item
        return None
    def load_memories(self, prefix:str=None):
        if prefix: self.set_prefix(prefix)
        self.memories.extend(self.rStore().get_all_from_store(self.key()))
        print(f"Loaded {len(self.memories)} memories.")
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


if __name__ == "__main__":
    mem = MemoryTool()
    mem.set_prefix('general2025.1')
    print(mem.search_memory("flower of life"))
