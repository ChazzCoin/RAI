
import time
import uuid

from F import LIST
from rai.agentic.ai_plugins.reason import rAssistantPlugin
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools


class MemoryAssistant(rAssistantPlugin):

    @staticmethod
    def key(session_id) -> str: return f"memory.{session_id}"

    @classmethod
    def request(cls, session_id:str, user_prompt: str, **attached_data):
        prompt = f"""
            user_id/session_id: {session_id}
            user_prompt: {user_prompt}
            data: {str(**attached_data)}
        """
        return cls().ask(user_prompt=prompt)

    """ QUICK NOTES MEMORY """

    @staticmethod
    def search_notes(session_id: str, user_prompt: str) -> str:
        query_embedding = MemoryAssistant.rAI().embed(user_prompt)
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().search_vector(
            collection_name=collection_name,
            vectors=query_embedding,
            limit=5,
            where={ "type": {"$eq": "note"} },
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this note."
        return top_result['document']

    @staticmethod
    def remember_note(session_id: str, note:str, **attached_data):
        interaction_text = f"Data: {attached_data}\n Note: {note}"
        interaction_id = str(uuid.uuid4())
        collection_name = MemoryAssistant.key(session_id)
        meta = {"session_id": session_id, "timestamp": time.time(), "type": "note" }
        MemoryAssistant.rStore().create_and_store(collection_name, id=interaction_id, text=interaction_text, metadata=meta)
        print(f"Stored note {interaction_id} for session {session_id}.")

    @staticmethod
    def retrieve_notes(session_id: str) -> str:
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().get_all(collection_name)
        if not results:
            return "No previous interactions found."
        return results

    @staticmethod
    def retrieve_last_note(session_id: str) -> str:
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().get_all(collection_name)
        if not results:
            return "No previous interactions found."
        last_interaction = sorted(
            results,
            key=lambda doc: doc.get("metadata", {}).get("timestamp", 0),
            reverse=True
        )[0]
        return last_interaction.get("document", "No document content found.")

    """ LONG TERM MEMORY """

    @staticmethod
    def search_memory(session_id: str, user_prompt: str) -> str:
        query_embedding = MemoryAssistant.rAI().embed(user_prompt)
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().search_vector(
            collection_name=collection_name,
            vectors=query_embedding,
            limit=5,
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this interaction."
        return top_result['document']

    @staticmethod
    def remember(session_id: str, memory_data:str, **attached_data):
        """ SAVE a General Memory """
        interaction_text = f"Data: {attached_data}\n Memory: {memory_data}"
        context_prompt = rTextTools.tool('summarize', user_prompt=interaction_text)
        interaction_text = interaction_text + f"\nSummarized Context: {context_prompt}"
        interaction_id = str(uuid.uuid4())
        collection_name = MemoryAssistant.key(session_id)
        meta = {"session_id": session_id, "timestamp": time.time(), "type": "long" }
        MemoryAssistant.rStore().create_and_store(collection_name, id=interaction_id, text=interaction_text, metadata=meta)
        print(f"Stored interaction {interaction_id} for session {session_id}.")

    @staticmethod
    def retrieve_memories(session_id: str) -> str:
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().get_all(collection_name)
        if not results:
            return "No previous interactions found."
        return results

    @staticmethod
    def retrieve_last_memory(session_id: str) -> str:
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.rStore().get_all(collection_name)
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
    user_prompt = "What do i need to do on Saturday March 8th 2025?"
    MemoryAssistant.request(user_id, user_prompt)
