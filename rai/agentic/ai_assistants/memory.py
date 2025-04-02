import time
import uuid
from datetime import datetime
from typing import Type

from F import LIST
from pydantic import BaseModel

from rai.agentic.pending.assist import pAssistant
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools


class rMemoryAssistant(pAssistant):
    session_id = None

    @staticmethod
    def module_name() -> str: return "MemoryAssistant"
    @staticmethod
    def assistant_rules() -> str:
        return ""
    """ TODO """
    @staticmethod
    def _required_data_model_type() -> BaseModel:
        pass
    @staticmethod
    def _required_model() -> Type[BaseModel]:
        pass

    def key(self) -> str: return f"memory.{self.session_id}"

    @classmethod
    def request(cls, session_id:str, user_prompt: str, **attached_data):
        prompt = f"""
            user_id/session_id: {session_id}
            user_prompt: {user_prompt}
            data: {str(**attached_data)}
        """
        self = cls()
        self.session_id = session_id
        return self.ask(user_prompt=prompt)
    @classmethod
    def init_session(cls, session_id:str):
        self = cls()
        self.session_id = session_id
        return self
    """ LOGGING MEMORY """
    def search_logs(self, query: str):
        """ """
        return rMemoryAssistant.rCache().query_store(
            prefix=self.key(),
            query=query,
        )
    def save_to_logs(self, message: str):
        """ """
        return rMemoryAssistant.rCache().add_text(
            prefix=self.key(),
            text=message,
            timestamp=int(datetime.utcnow().timestamp())
        )
    def retrieve_logs(self):
        """ """
        results = rMemoryAssistant.rCache().get_documents_by_tag(tag=self.key())
        return results
    """ QUICK NOTES MEMORY """
    def search_notes(self, user_prompt: str) -> str:
        """ """
        query_embedding = rMemoryAssistant.rAI().embed(user_prompt)
        results = rMemoryAssistant.rStore().search_vector(
            collection_name=self.key(),
            vectors=query_embedding,
            limit=5,
            where={ "type": {"$eq": "note"} },
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this note."
        return top_result['document']
    def save_note(self, note:str, **attached_data):
        """ """
        interaction_text = f"Data: {attached_data}\n Note: {note}"
        interaction_id = str(uuid.uuid4())
        meta = {"session_id": self.session_id, "timestamp": time.time(), "type": "note" }
        rMemoryAssistant.rStore().create_and_store(self.key(), id=interaction_id, text=interaction_text, metadata=meta)
        self.assistant_log(f"Stored note {interaction_id} for session {self.session_id}.")
    def retrieve_notes(self) -> str:
        """ """
        collection_name = rMemoryAssistant.key(self.session_id)
        results = rMemoryAssistant.rStore().get_all(collection_name)
        if not results:
            return "No previous interactions found."
        return results
    def retrieve_last_note(self) -> str:
        """ """
        results = rMemoryAssistant.rStore().get_all(self.key())
        if not results:
            return "No previous interactions found."
        last_interaction = sorted(
            results,
            key=lambda doc: doc.get("metadata", {}).get("timestamp", 0),
            reverse=True
        )[0]
        return last_interaction.get("document", "No document content found.")
    """ LONG TERM MEMORY """
    def search_long_term_memory(self, user_prompt: str) -> str:
        """ """
        query_embedding = rMemoryAssistant.rAI().embed(user_prompt)
        results = rMemoryAssistant.rStore().search_vector(
            collection_name=self.key(),
            vectors=query_embedding,
            limit=5,
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this interaction."
        return top_result['document']
    def save_to_long_term(self, memory_data:str, **attached_data):
        """ SAVE a General Memory """
        interaction_text = f"Data: {attached_data}\n Memory: {memory_data}"
        context_prompt = rTextTools.tool('summarize', user_prompt=interaction_text)
        interaction_text = interaction_text + f"\nSummarized Context: {context_prompt}"
        interaction_id = str(uuid.uuid4())
        meta = {"session_id": self.session_id, "timestamp": time.time(), "type": "long" }
        rMemoryAssistant.rStore().create_and_store(self.key(), id=interaction_id, text=interaction_text, metadata=meta)
        self.assistant_log(f"Stored interaction {interaction_id} for session {self.session_id}.")
    def retrieve_from_long_term(self) -> str:
        """ """
        results = rMemoryAssistant.rStore().get_all(self.key())
        if not results:
            return "No previous interactions found."
        return results
    def retrieve_last_long_term_memory(self) -> str:
        """ """
        results = rMemoryAssistant.rStore().get_all(self.key())
        if not results:
            return "No previous interactions found."
        last_interaction = sorted(
            results,
            key=lambda doc: doc.get("metadata", {}).get("timestamp", 0),
            reverse=True
        )[0]
        return last_interaction.get("document", "No document content found.")


# Example usage:
if __name__ == "__main__":
    user_id = "user_123"
    user_prompt = "AHHH WE HAVE A HORRIBLE BAD ERROR"
    results = rMemoryAssistant.init_session(user_id).retrieve_logs()
    print(results)
