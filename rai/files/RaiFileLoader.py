import uuid
from rai import app
from F.LOG import Log
from tqdm import tqdm
from rai.utils.utils import progress_bar
from pathlib import Path
from rai.files import RaiPath
from rai.files.RaiDataLoaders import RaiDataLoader
from datetime import datetime
from rai.constants import ERROR_MESSAGES
from rai.RAG.connector import VECTOR_DB_CLIENT
from assistant.ollama_client import generate_chroma_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
Log = Log("Rai File Loader")

class RaiFileLoader:
    collection_prefix: str = None
    base_directory:RaiPath = None
    current_file:str = "None"

    def __init__(self, base_directory: str, collection_prefix:str=str(uuid.uuid4())):
        self.base_directory = RaiPath(base_directory)
        self.collection_prefix = collection_prefix

    def import_directory_into_chroma(self, collection_prefix :str=None):
        """
        Loop through all directories inside the base directory,
        each subdirectory represents a collection name for Chroma DB.
        """
        if collection_prefix is not None:
            self.collection_prefix = collection_prefix
        for sub_dir in self.base_directory.list_directory(files_only=False):
            Log.i(f"Starting Import [ {sub_dir} ]")
            if sub_dir.is_dir():
                d_name = sub_dir.name
                collection_name = f"{self.collection_prefix}-{d_name}"
                self._process_collection(sub_dir, collection_name)

        Log.s("Completed Document scanning.")
        return True
    def _process_collection(self, directory: Path, collection_name: str):
        """
        Processes a single collection represented by the subdirectory.
        """
        # Assuming RaiPath handles directory paths for yielding files
        raiFile = RaiPath(directory)
        for path in raiFile.list_directory(files_only=False):
            try:
                if path.is_dir():
                    continue
                filename = path.name
                # Open the file for processing
                Log.i(f"Processing: [ {path} ] for Collection: [ {collection_name} ]")
                loader = RaiDataLoader(path).loader
                data = loader.load()

                # Storing the data into vector DB
                try:
                    Log.i(f"Saving: {filename}")
                    result = self.store_data_in_vector_db(data, collection_name)
                    if result:
                        Log.s(f"Saved: [ {filename} ]")

                except Exception as e:
                    Log.e(f"Error saving data for file '{filename}' to Chroma DB: {e}")
                    continue

            except Exception as e:
                Log.e(f"Error processing file '{path}': {e}")
                continue
    def store_data_in_vector_db(self, data, collection_name):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )

        docs = text_splitter.split_documents(data)

        if len(docs) > 0:
            return self.__store_docs_in_vector_db(docs, collection_name)
        else:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
    def store_text_in_vector_db(self, text, metadata, collection_name, overwrite:bool=False) -> bool:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
        docs = text_splitter.create_documents([text], metadatas=[metadata])
        return self.__store_docs_in_vector_db(docs, collection_name, overwrite=overwrite)
    def __store_docs_in_vector_db(self, docs, collection_name, overwrite:bool=False):
        Log.i(f"importing [ {len(docs)} ] docs in [ {collection_name} ]")

        texts = [doc.page_content for doc in docs]
        metadatas = [{**doc.metadata, **({})} for doc in docs]
        # ChromaDB does not like datetime formats
        # for meta-data so convert them to string.
        Log.i("Preparing metadata for chromadb...")
        for metadata in tqdm(metadatas, "Preparing metadata for chromadb...", colour="yellow"):
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    metadata[key] = str(value)
        try:
            if overwrite:
                if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
                    Log.w(f"deleting existing collection {collection_name}")
                    VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
            else:

                items = []
                for idx, txt in enumerate(tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")):
                    temp = {
                        "id": str(uuid.uuid4()),
                        "text": txt,
                        "vector": generate_chroma_embeddings(text=txt),
                        "metadata": metadatas[idx],
                    }
                    items.append(temp)

                VECTOR_DB_CLIENT.insert(
                    collection_name=collection_name,
                    items=items,
                )
                return True
        except Exception as e:
            Log.e(e)
            return False
    @staticmethod
    def delete_collections(*collections:str):
        for collection in collections:
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection)
            except Exception as e:
                Log.e(e)


""" -> public INTAKE <- """


# def store_doc(collection_name: Optional[str], file: RaiPath):
#     Log.i(f"Processing file: {file}")
#     try:
#         filename = file.file_name
#
#         # Guess the content type based on the file extension
#         content_type, encoding = mimetypes.guess_type(file.path)
#         Log.i(f"Detected content_type: {content_type}")
#
#         if collection_name is None:
#             with open(file.path, "rb") as f:
#                 collection_name = calculate_sha256(f)[:63]
#
#         loader = RaiDataLoader(file.path).loader
#         data = loader.load()
#
#         try:
#             result = store_data_in_vector_db(data, collection_name)
#
#             if result:
#                 return {
#                     "status": True,
#                     "collection_name": collection_name,
#                     "filename": filename,
#                     "known_type": file.ext_type,
#                 }
#             else:
#                 return {}
#         except Exception as e:
#             Log.e(e)
#             return {}
#     except Exception as e:
#         Log.e(e)
#         if "No pandoc was found" in str(e):
#             return {}
#         else:
#             return {}

