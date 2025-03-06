
import time
import uuid

from F import LIST
from rai.agentic.ai_plugins.curator_plugin import CuratorPlugin
from rai.agentic.connectors import VECTOR_STORE
from rai.assistant.openai_client import generate_embeddings


class MemoryStore(CuratorPlugin):

    @staticmethod
    def store(): return VECTOR_STORE

    @classmethod
    def memory_request(cls, session_id:str, user_prompt: str, ai_response:str=None, **attached_data):
        prompt = f"""
            user_id/session_id: {session_id}
            user_prompt: {user_prompt}
            ai_response: {ai_response}
            data: {str(attached_data)}           
            GOAL: If no 'ai_response' then we want to retrieve, else store.
        """
        return cls().ask(user_prompt=prompt)

    @staticmethod
    def store_interaction(user_id: str, user_prompt:str, ai_response:str, **attached_data):
        interaction_text = f"Data: {attached_data}\n User: {user_prompt}\n AI: {ai_response}"
        interaction_id = str(uuid.uuid4())
        collection_name = f"memory.{user_id}"
        meta = {"user_id": user_id, "timestamp": time.time()}
        MemoryStore.store().create_and_store(collection_name, id=interaction_id, text=interaction_text, metadata=meta)
        print(f"Stored interaction {interaction_id} for user {user_id}.")

    @staticmethod
    def retrieve_interaction(user_id: str, user_prompt: str, n_results: int = 5) -> str:
        query_embedding = generate_embeddings(user_prompt)
        collection_name = f"memory.{user_id}"
        results = MemoryStore.store().search_vector(
            collection_name=collection_name,
            vectors=query_embedding,
            limit=n_results,
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this interaction."
        # context_prompt = R.text_tool('summarize', user_prompt=top_result['document'])
        return top_result['document']

    @staticmethod
    def retrieve_last_interaction(user_id: str) -> str:
        """
        Retrieve the most recent (last) stored interaction for a given user by timestamp.
        """
        collection_name = f"memory.{user_id}"
        results = MemoryStore.store().get_all(collection_name)
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
    user_prompt = "what is the last interaction?"
    # ai_response = "at the park near your house of course!"
    ai_response = None
    MemoryStore.memory_request(user_id, user_prompt, ai_response)
