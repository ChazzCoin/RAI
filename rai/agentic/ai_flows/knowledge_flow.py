from rai.agentic.ai_plugins.function_caller import FunctionCallPlugin, TestCaller
from rai.assistant.connectors import rAI
from rai.internal.chromadb import ChromaClient
from F.LOG import Log

Log = Log("KnowledgeFlow")


class rKnowledgeFlow(FunctionCallPlugin, ChromaClient):
    """
    A Document Manager that extends the ChromaClient to support AI-driven document management.
    It uses a provided 'prefix' to namespace and manage documents within a specific collection.
    """

    @classmethod
    def flow(cls, prefix:str, user_prompt:str, engine='openai'):
        return cls(prefix=prefix, engine=engine).decide_and_call(user_prompt)

    def __init__(self, prefix: str, sub_collection:str="pages", engine='openai'):
        super().__init__(engine=engine)
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

    def execute_function_call(self, call_data: dict):
        """
        Executes a function based on the AI agent's function call result.

        The call_data dictionary should have the following structure:

        {
          "name": "function_name",
          "parameters": { ... }
        }

        Supported functions include:
          - get_all_documents
          - browse_documents (optional parameter: limit)
          - get_document_by_id (required parameter: doc_id)
          - delete_document (required parameter: doc_id)
          - update_document (required parameters: doc_id, new_text, new_vector, and optional new_metadata)

        :param call_data: A dictionary with keys "name" and "parameters".
        :return: The result from the function call.
        """
        try:
            function_name = call_data.get("name")
            parameters = call_data.get("parameters", {})

            if function_name == "get_all_documents":
                return self.get_all_documents()

            elif function_name == "browse_documents":
                limit = parameters.get("limit")
                if limit is not None:
                    return self.browse_documents(limit=limit)
                else:
                    return self.browse_documents()

            elif function_name == "get_document_by_id":
                doc_id = parameters.get("doc_id")
                if not doc_id:
                    raise ValueError("Missing required parameter 'doc_id' for get_document_by_id")
                return self.get_document_by_id(doc_id)

            elif function_name == "delete_document":
                doc_id = parameters.get("doc_id")
                if not doc_id:
                    raise ValueError("Missing required parameter 'doc_id' for delete_document")
                self.delete_document(doc_id)
                return f"Document with ID '{doc_id}' has been deleted."

            elif function_name == "update_document":
                doc_id = parameters.get("doc_id")
                new_text = parameters.get("new_text")
                if not doc_id or new_text is None:
                    raise ValueError("Missing required parameters for update_document")
                self.update_document(doc_id, new_text)
                return f"Document with ID '{doc_id}' has been updated."

            else:
                raise ValueError(f"Unknown function call: {function_name}")

        except Exception as e:
            Log.e(f"Error executing function call: {e}")
            raise e


if __name__ == "__main__":
    results = rKnowledgeFlow.flow("rai2025.1", "show the document with id 6765fcfb-68ca-41f8-a0c1-58ee67587094:0", engine='ollama')
    print(results)
