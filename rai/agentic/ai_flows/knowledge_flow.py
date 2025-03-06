from rai.agentic.ai_flows.r_flows import rFlows, register_flow
from rai.agentic.ai_plugins.curator_plugin import CuratorPlugin, TestCaller
from rai.assistant.connectors import rAI
from rai.internal.chromadb import ChromaClient
from F.LOG import Log

Log = Log("KnowledgeFlow")


@register_flow("knowledge-curator")
class rKnowledgeFlow(CuratorPlugin, ChromaClient, rFlows):
    """
    A Document Manager that extends the ChromaClient to support AI-driven document management.
    It uses a provided 'prefix' to namespace and manage documents within a specific collection.
    """
    name = None
    @classmethod
    def flow(cls, name:str, prefix:str, user_prompt:str, engine='openai'):
        return cls(name=name, prefix=prefix, engine=engine).decide_and_call(user_prompt)
    @classmethod
    def exec(cls, name, prefix:str, user_prompt:str, engine='openai'):
        return cls(name=name, prefix=prefix, engine=engine).decide_and_call(user_prompt)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __init__(self, name:str, prefix: str, sub_collection:str="pages", engine='openai'):
        super().__init__(engine=engine)
        self.name = name
        self.init()
        self.prefix = f"{prefix}.{sub_collection}"
        Log.s(f"Document Manager initialized with prefix: {self.prefix}")

    def get_all_documents(self):
        """
        Retrieve all documents from the collection defined by the prefix.
        Returns the raw result from the parent's 'get' method.
        """
        return self.get(self.prefix, combined=True)
    def browse_documents(self, limit: int = None):
        """
        Retrieve and format all documents from the collection into a browsable list.
        Each document is represented as a dictionary with keys: 'id', 'document', 'metadata'.

        :param limit: Optional; limit the number of documents returned.
        :return: List of dictionaries representing documents.
        """
        result = self.get(self.prefix, combined=True)
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

        :param doc_id: The unique identifier of the document to delete.
        """
        Log.s(f"Attempting to delete document with ID: {doc_id}")
        self.delete(self.prefix, [doc_id])
        Log.s(f"Document with ID '{doc_id}' deleted.")
    def update_document(self, doc_id: str="1", new_text: str="new"):
        """
        Update an existing document with new text, vector, and optionally new metadata.
        Utilizes the upsert operation, so if the document doesn't exist, it will be inserted.

        :param doc_id: The unique identifier for the document.
        :param new_text: The updated document text.
        :param new_vector: The updated embedding vector for the document.
        :param new_metadata: Optional dictionary of updated metadata.
        """
        Log.s(f"Updating document with ID: {doc_id}")
        item = {
            "id": doc_id,
            "text": new_text,
            "vector": rAI('openai').embed(new_text),
            "metadata": {'type': 'ai modifications'}
        }
        self.upsert(self.prefix, [item])
        Log.s(f"Document with ID '{doc_id}' updated.")


if __name__ == "__main__":
    results = rKnowledgeFlow.flow("rai2025.1", "show the document with id 6765fcfb-68ca-41f8-a0c1-58ee67587094:0", engine='ollama')
    print(results)
