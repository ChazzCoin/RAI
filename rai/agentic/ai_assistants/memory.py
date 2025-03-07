
import time
import uuid

from F import LIST
from rai.agentic.ai_plugins.curator import rCuratorPlugin
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools


class MemoryAssistant(rCuratorPlugin):

    @staticmethod
    def key(session_id) -> str: return f"memory.{session_id}"

    @classmethod
    def request(cls, session_id:str, user_prompt: str, ai_response:str=None, **attached_data):
        prompt = f"""
            user_id/session_id: {session_id}
            user_prompt: {user_prompt}
            ai_response: {ai_response}
            data: {str(attached_data)}           
            GOAL: If no 'ai_response' then we want to retrieve, else store.
        """
        return cls().ask(user_prompt=prompt)

    @staticmethod
    def store_interaction(session_id: str, user_prompt:str, ai_response:str, **attached_data):
        interaction_text = f"Data: {attached_data}\n User: {user_prompt}\n AI: {ai_response}"
        context_prompt = rTextTools.tool('summarize', user_prompt=interaction_text)
        interaction_text = interaction_text + f"\nContext: {context_prompt}"
        interaction_id = str(uuid.uuid4())
        collection_name = MemoryAssistant.key(session_id)
        meta = {"session_id": session_id, "timestamp": time.time()}
        MemoryAssistant.rStore().create_and_store(collection_name, id=interaction_id, text=interaction_text, metadata=meta)
        print(f"Stored interaction {interaction_id} for session {session_id}.")

    @staticmethod
    def retrieve_interaction(session_id: str, user_prompt: str) -> str:
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
    def retrieve_last_interaction(session_id: str) -> str:
        """
        Retrieve the most recent (last) stored interaction for a given user by timestamp.
        """
        collection_name = MemoryAssistant.key(session_id)
        results = MemoryAssistant.store().get_all(collection_name)
        if not results:
            return "No previous interactions found."
        last_interaction = sorted(
            results,
            key=lambda doc: doc.get("metadata", {}).get("timestamp", 0),
            reverse=True
        )[0]
        return last_interaction.get("document", "No document content found.")

    """ todo: -> attach to user_prompt as a passthrough ... """

# Example usage:
if __name__ == "__main__":
    user_id = "user_123"
    user_prompt = "what is the last interaction?"
    # ai_response = "at the park near your house of course!"
    ai_response = None
    MemoryAssistant.request(user_id, user_prompt, ai_response)
