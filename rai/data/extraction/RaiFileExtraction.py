import uuid
from rai import app
from F.LOG import Log
from tqdm import tqdm
from pathlib import Path
from rai.data import RaiPath
from datetime import datetime
from rai.constants import ERROR_MESSAGES
from rai.RAG.connector import VECTOR_DB_CLIENT
from rai.assistant.ollama_client import generate_chroma_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from rai.data.loaders import RaiDataLoaders

Log = Log("RaiFileExtractor")

class RaiFileExtractor:
    pipeline: str = "chroma"
    collection_prefix: str = None
    base_directory:RaiPath = None
    current_file:str = "None"
    file_to_import_by_collection: {str:list} = {}
    file_to_import_count = 0

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
        Log.i(f"Preparing Files for Import: [ {self.base_directory} ]")
        for sub_dir in self.base_directory.list_directory(files_only=False):
            if sub_dir.is_dir():
                d_name = sub_dir.name
                collection_name = f"{self.collection_prefix}-{d_name}"
                raiDirectory = RaiPath(sub_dir)
                file_list = []
                for files in raiDirectory.list_directory(files_only=False):
                    file_list.append(files)
                    self.file_to_import_count += 1
                self.file_to_import_by_collection[collection_name] = file_list

        Log.s(f"Starting Import: Total [ {self.file_to_import_count} ]")
        for collection_name in self.file_to_import_by_collection.keys():
            files_to_handle = self.file_to_import_by_collection[collection_name]
            for file in files_to_handle:
                self.process_file(file, collection_name)

        Log.s(f"Finished Importing Files: Total [ {self.file_to_import_count} ]")
        return True
    def process_file(self, file: Path, collection_name: str):
        """
        Processes a single collection represented by the subdirectory.
        """
        # Assuming RaiPath handles directory paths for yielding files
        raiFile = RaiPath(file)
        try:
            if raiFile.is_directory:
                return
            # Open the file for processing
            Log.i(f"Processing: [ {raiFile} ] for Collection: [ {collection_name} ]")
            loader = RaiDataLoaders.RaiDataLoader(raiFile).loader
            data = loader.load()
            try:
                result = self.batch_data(data, collection_name)
                if result:
                    Log.s(f"Finished Importing: [ {raiFile.file_name} ]")
            except Exception as e:
                Log.w(f"Error importing file '{raiFile.file_name}' to Chroma DB: {e}")
        except Exception as e:
            Log.w(f"Error importing file '{raiFile}': {e}")
    def batch_data(self, data, collection_name):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
        docs = text_splitter.split_documents(data)
        if len(docs) > 0: return self.__store_docs_in_vector_db(docs, collection_name)
        else: raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
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

