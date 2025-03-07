import time

from rai.agentic.ai_flows.r_flows import rFlows, register_flow
from rai.agentic.ai_plugins.curator import rCuratorPlugin
from F.LOG import Log

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
class KnowledgeAssistant(rCuratorPlugin):
    """
    A Document Manager that extends the ChromaClient to support AI-driven document management.
    It uses a provided 'prefix' to namespace and manage documents within a specific collection.
    """
    assistant = "knowledge"
    sub_collection: str = "pages"
    @classmethod
    def request(cls, prefix:str, user_prompt:str):
        return cls(prefix=prefix).decide_and_call(user_prompt)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __init__(self, prefix: str):
        super().__init__()
        self.rStore().init()
        self.prefix = f"{prefix}.{self.sub_collection}"
        Log.s(f"Document Manager initialized with prefix: {self.prefix}")

    def get_all_documents(self):
        return self.rStore().get(self.prefix, combined=True)

    def browse_documents(self, limit: int = None):
        """
        Retrieve and format all documents from the collection into a browsable list.
        Each document is represented as a dictionary with keys: 'id', 'document', 'metadata'.
        """
        result = self.rStore().get(self.prefix, combined=True)
        if not result:
            Log.e("No documents found in the collection.")
            return []

        if limit is not None:
            result = result[:limit]
        return result
    def get_document_by_id(self, doc_id="1"):
        """
        Retrieve a single document by its ID.

        :param doc_id: The unique identifier for the document.
        :return: A dictionary with keys 'id', 'document', 'metadata' if found, else None.
        """
        documents = self.browse_documents()
        for doc in documents:
            if doc["id"] == doc_id:
                return doc
        Log.w(f"Document with ID '{doc_id}' not found.")
        return None
    def delete_document(self, doc_id: str="1"):
        """
        Delete a document from the collection based on its ID.
        """
        Log.s(f"Attempting to delete document with ID: {doc_id}")
        self.rStore().delete(self.prefix, [doc_id])
        Log.s(f"Document with ID '{doc_id}' deleted.")
    def update_document(self, doc_id: str="1", new_text: str="new"):
        """
        Update an existing document with new text, vector, and optionally new metadata.
        Utilizes the upsert operation, so if the document doesn't exist, it will be inserted.
        """
        Log.s(f"Updating document with ID: {doc_id}")
        item = {
            "id": doc_id,
            "text": new_text,
            "vector": self.rAI().embed(new_text),
            "metadata": {'type': 'ai modifications', 'timestamp': time.time() },
        }
        self.rStore().upsert(self.prefix, [item])
        Log.s(f"Document with ID '{doc_id}' updated.")


if __name__ == "__main__":
    results = KnowledgeAssistant.request("rai2025.1", "show the document with id 6765fcfb-68ca-41f8-a0c1-58ee67587094:0")
    print(results)
