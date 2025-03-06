
import time
import uuid

from F import LIST
from rai.agentic.ai_plugins.QStore import VectorStore
from rai.agentic.ai_plugins.curator_plugin import CuratorPlugin
from rai.assistant.connectors import R


class MemoryStore(CuratorPlugin):

    store = VectorStore()

    @classmethod
    def memory(cls, user_id: str, user_prompt: str, ai_response: str=None):
        prompt = f"""
            user_id: {user_id}
            user_prompt: {user_prompt}
            ai_response: {ai_response}
            
            GOAL: If no 'ai_response' then we want to retrieve, else store.
        """
        return cls().request(user_prompt=prompt)

    @classmethod
    def memory_in(cls, user_id: str, user_prompt: str, ai_response: str=None):
        return cls().store_interaction(user_id=user_id, user_prompt=user_prompt, ai_response=ai_response)

    @classmethod
    def memory_out(cls, user_id: str, user_prompt: str):
        return cls().retrieve_interaction(user_id=user_id, user_prompt=user_prompt)

    # Store an interaction (user prompt and AI response) in the memory store
    def store_interaction(self, user_id: str, user_prompt: str, ai_response: str):
        # Combine the interaction into a single memory document
        interaction_text = f"User: {user_prompt}\nAI: {ai_response}"
        interaction_id = str(uuid.uuid4())
        collection_name = f"memory.{user_id}"
        meta = {"user_id": user_id, "timestamp": time.time()}
        self.store.create_and_store(collection_name, id=interaction_id, text=interaction_text, metadata=meta)
        print(f"Stored interaction {interaction_id} for user {user_id}.")

    # Retrieve relevant memories and compile a concise context prompt for the current query
    def retrieve_interaction(self, user_id: str, user_prompt: str, n_results: int = 5) -> str:
        # Generate the embedding for the current query
        query_embedding = R.embed(user_prompt)
        # Query the collection for similar documents, filtering by the user_id
        collection_name = f"memory.{user_id}"
        results = self.store.search_vector(
            collection_name=collection_name,
            vectors=query_embedding,
            limit=n_results,
            combined=True
        )
        top_result = LIST.get(0, results, None)
        if not top_result: return "No previous memory for this interaction."
        # context_prompt = R.text_tool('summarize', user_prompt=top_result['document'])
        return top_result['document']

# Example usage:
if __name__ == "__main__":
    # These values would typically come from your API’s request data
    user_id = "user_123"
    user_prompt = "database"
    # ai_response = "at the park near your house of course!"
    ai_response = None
    MemoryStore.memory(user_id, user_prompt, ai_response)
