import uuid
import tiktoken
from pydantic import UUID4

# from lxml.parser import result

from config.chroma import ChromaInstance, ChromaDocument
from assistant.openai_client import generate_embeddings
import os
from config import env
import openai  # Or another embedding model you'd like to use
from dataset.DataCleaner import process_file, to_sentences, to_paragraphs, to_paragraphs_with_min_max

"""
            DEPRECATED FOR RAG
"""

class EmbeddingProcessor:

    def __init__(self, collection_name):
        self.chroma_instance = ChromaInstance(collection_name=collection_name, persistent=True)

    def tokenize_text(self, text: str):
        return

    def chunk_text(self, tokens: list):
        return

    def detokenize(self, tokens: list):
        return

    def process_raw_text_file(self, raw_text: str, doc_name: str, metadata=None):
        try:
            # Tokenize the raw text
            paragraphs = to_paragraphs_with_min_max(raw_text)
            for paragraph in paragraphs:
                doc_embeddings = generate_embeddings(paragraph)
                new_doc = ChromaDocument(doc_id=str(uuid.uuid4()), doc_text=paragraph, doc_metadata={}, doc_embeddings=doc_embeddings)
                # Add metadata
                new_doc.metadata(title=doc_name)
                # Insert the document into the Chroma instance
                if new_doc.doc_embeddings:
                    self.chroma_instance.insert_document(new_doc.toJson())
        except Exception as e:
            print(f"Error processing the text file: {e}")

class TextToChroma:
    def __init__(self, collection_name):
        """
        Initialize the TextToChroma class with the provided ChromaInstance.
        Args:
            chroma_instance (ChromaInstance): An instance of the ChromaInstance class.
            openai_api_key (str, optional): OpenAI API key for generating embeddings. Defaults to None.
        """
        self.chroma_instance = ChromaInstance(collection_name=collection_name)

    def create_embedding(self, text):
        """
        Creates an embedding for the given text using OpenAI or any other service.
        Replace this with your embedding provider or model.
        """
        try:
            return generate_embeddings(text)
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return None

    def process_text_file(self, txt_file, metadata=None):
        """
        Processes the .txt file, generates embeddings for each section/line, and uploads
        the data to ChromaDB with metadata using the ChromaInstance.
        """
        if not os.path.isfile(txt_file):
            print(f"Error: {txt_file} does not exist.")
            return

        try:
            # Initialize a list to store lines with metadata
            documents = []

            # Open and read the file
            with open(txt_file, 'r', encoding='utf-8') as file:
                content = file.readlines()

            # Iterate over each line in the text file
            for line_number, line in enumerate(content, start=1):
                cleaned_line = line.strip()  # Clean unnecessary whitespace

                if cleaned_line:  # Only process non-empty lines
                    # Create metadata for this specific line
                    line_metadata = {
                        "file_name": os.path.basename(txt_file),
                        "line_number": line_number,
                        "text_snippet": cleaned_line[:50],  # First 50 chars as a preview
                    }

                    # Merge additional metadata if provided
                    if metadata:
                        line_metadata.update(metadata)

                    # Create embedding for the line
                    embedding = self.create_embedding(cleaned_line)

                    if embedding:
                        # Create a document dictionary with ID, text, metadata, and embeddings
                        documents.append({
                            "id": f"{os.path.basename(txt_file)}_line_{line_number}",
                            "text": cleaned_line,
                            "metadata": line_metadata,
                            "embeddings": embedding
                        })

            # Insert all documents in a batch to ChromaDB via ChromaInstance
            self.chroma_instance.batch_insert(documents)

        except Exception as e:
            print(f"Error processing the text file: {e}")

    def process_raw_text_file(self, raw_text: str, doc_name:str, metadata=None):
        try:
            # Initialize a list to store lines with metadata
            new_doc = ChromaDocument(doc_id=doc_name, doc_text=raw_text, doc_metadata={}, doc_embeddings=[])
            # Create embedding for the line
            new_doc.doc_embeddings = self.create_embedding(raw_text)
            new_doc.metadata(topic='soccer', source='park city', author='website')
            if new_doc.doc_embeddings:
                self.chroma_instance.insert_doc(new_doc)
        except Exception as e:
            print(f"Error processing the text file: {e}")


def process_raw_text_file(raw_text: str, doc_name: str):
    results = []
    try:
        paragraphs = to_paragraphs_with_min_max(raw_text)
        for paragraph in paragraphs:
            results.append({
                'id': str(uuid.uuid4()),
                'text': paragraph,
                'metadata': {'title': doc_name}
            })
        return results
    except Exception as e:
        print(f"Error processing the text file: {e}")
        return results
if __name__ == '__main__':
    from dataset import load_txt_file
    from config.chroma import ChromaInstance
    from assistant.rag import RAGWithChroma
    # croma = ChromaInstance(collection_name='city_park')
    # results = croma.query("futures program")
    # print(results)

