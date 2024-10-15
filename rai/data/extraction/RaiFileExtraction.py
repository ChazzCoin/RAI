import time
import uuid
from distutils.command.config import config

from F.CLASS import Flass
from rai import app
from F.LOG import Log
from tqdm import tqdm
from pathlib import Path
from rai.data import RaiPath
from datetime import datetime
from rai.RAG.connector import VECTOR_DB_CLIENT
from rai.assistant.ollama_client import generate_chroma_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from rai.data.loaders import RaiDataLoaders
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiBaseLoader
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader

Log = Log("RaiFileExtractor")


class RaiConfig(Flass):
    pipeline: str = "print"
    collection_prefix: str = None
    base_path: RaiPath = None
    overwrite: bool = False
    split_documents: bool = False
    metadatas: [dict] = None
    generate_ai_metadata: bool = False
    meta_loader: RaiMetadataLoader = None
    text_splitter: RecursiveCharacterTextSplitter = None

class RaiFileExtractor:
    config = RaiConfig()
    current_file: RaiPath = None
    file_to_import_by_collection: {str:list} = {}
    file_to_import_count = 0

    class Pipelines:
        PRINT = "print"
        CHROMA = "chroma"

    def __init__(self, pipeline:str, base_directory: str, collection_prefix:str=str(uuid.uuid4())):
        self.config.pipeline = pipeline
        self.config.base_path = RaiPath(base_directory)
        self.config.collection_prefix = collection_prefix
        self.current_file = RaiPath(base_directory)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
    @classmethod
    def fromConfig(cls, raifig:RaiConfig):
        newcls = cls(raifig.pipeline, RaiPath(raifig.base_path), raifig.collection_prefix)
        newcls.config = raifig
        return newcls

    def run(self, collection_prefix:str=None):
        if self.config.base_path.is_directory:
            self.import_directory(collection_prefix)
        elif self.config.base_path.is_file:
            self.import_file(collection_prefix)

    def import_directory(self, collection_prefix: str = None, directory_path: str = None):
        if directory_path is not None:
            self.config.base_path = RaiPath(directory_path)
        if collection_prefix is not None:
            self.config.collection_prefix = collection_prefix

        Log.i(f"Preparing Files for Import: [ {self.config.base_path} ]")
        self.file_to_import_count = 0
        self.file_to_import_by_collection = {}

        # Recursively traverse the directory tree starting from base_path
        for file_path in self.config.base_path.path.rglob('*'):
            if file_path.is_file():
                # Construct the relative path from base_path to the file's parent directory
                rel_path = file_path.parent.relative_to(self.config.base_path)
                path_parts = rel_path.parts  # Get the parts of the relative path
                # Construct the collection name by joining the collection prefix and path parts
                collection_name = '.'.join([self.config.collection_prefix] + list(path_parts))
                # Add the file to the corresponding collection
                self.file_to_import_by_collection.setdefault(collection_name, []).append(file_path)
                self.file_to_import_count += 1

        # Proceed with the import process
        Log.s(f"Starting Import: Total [ {self.file_to_import_count} ]")
        for collection_name, files_to_handle in self.file_to_import_by_collection.items():
            # First, handle metadata files
            if not str(collection_name).__contains__('.'):
                continue
            for file in files_to_handle:
                if RaiPath(file).is_metadata_file():
                    self.meta_loader = RaiMetadataLoader(meta_file=file)
            # Then, handle document files
            for file in files_to_handle:
                if RaiPath(file).is_metadata_file():
                    continue
                if str(file).endswith('.DS_Store'):
                    continue
                """
                    Handle Naming...
                    csv, xlsx need to be their own collection.
                """
                self.current_file = RaiPath(file)
                chained_collection_name = collection_name
                if self.current_file.ext_type in ['csv', 'xlsx']:
                    file_collection_name = RaiPath.sanitize_file_name_for_chromadb(self.current_file)
                    chained_collection_name = f"{chained_collection_name}-{file_collection_name}"
                # self.import_file(collection_name)
                print(f"Final Collection Name: [ {chained_collection_name} ] \nFile: [ {self.current_file.file_name} ]\n")
        Log.s(f"Finished Importing Files: Total [ {self.file_to_import_count} ]")
        return True

    def import_file(self, collection_name: str, file_path:str=None):
        try:
            if file_path is not None:
                self.config.base_path = RaiPath(file_path)
                self.current_file = RaiPath(file_path)
            if self.current_file.is_directory: return
            Log.i(f"Processing: [ {self.current_file.file_name} ] for Collection: [ {collection_name} ]")
            loader = RaiDataLoaders.RaiDataLoader(self.current_file, meta_loader=self.meta_loader).loader
            try:
                result = self.__run_pipeline(collection_name, loader=loader)
                if result: Log.s(f"Finished Importing: [ {self.current_file.file_name} ]")
            except Exception as e: Log.w(f"Error importing file '{self.current_file.file_name}' to Chroma DB: {e}")
        except Exception as e: Log.w(f"Error importing file '{self.current_file}': {e}")

    def __run_pipeline(self, collection_name:str, docs:[]=None, loader:RaiBaseLoader=None):
        if not docs: docs = loader.load()
        if self.config.split_documents:
            docs = self.__split_docs_into_smaller_chunks(docs)
        if self.config.pipeline.lower() == "chroma": return self.to_chroma(docs, collection_name)
        elif self.config.pipeline.lower() == "print": return self.to_printer(docs, collection_name)

    def to_printer(self, docs:[], collection_name:str):
        Log.w(f"Printing File: [ {RaiPath(self.current_file).file_name} ] Collection: [ {collection_name} ]")
        time.sleep(1)
        count = 0
        for d in docs:
            print(f"Record [ {count} ] [ {collection_name} ]:\n {d.page_content}")
            count += 1
            time.sleep(1)

    def to_chroma(self, docs:[], collection_name:str):
        Log.i(f"importing [ {len(docs)} ] docs in [ {collection_name} ]")
        texts = self.get_texts(docs)
        metadatas = self.prepare_metadatas(docs)
        items = self.prepare_chroma_documents(texts, metadatas)
        try:
            self.overwrite_collection_check(collection_name)
            VECTOR_DB_CLIENT.insert(
                collection_name=collection_name,
                items=items,
            )
            return True
        except Exception as e:
            Log.e(e)
            return False

    @staticmethod
    def get_texts(docs: []):
        metadatas = [doc.page_content for doc in docs]
        return metadatas

    @staticmethod
    def get_metadatas(docs: []):
        metadatas = [{**doc.metadata, **({})} for doc in docs]
        return metadatas

    def prepare_metadatas(self, docs: []):
        metadatas = []
        if self.config.generate_ai_metadata:
            doc_count = len(docs)
            if self.config.meta_loader is None:
                self.config.meta_loader = RaiMetadataLoader()
            d = self.get_texts(docs)
            meta = self.config.meta_loader.generate_ai_metadata_docs(data=d)
            for i in range(doc_count):
                metadatas.append(meta.toJson())
        else:
            metadatas = RaiFileExtractor.get_metadatas(docs)
        for metadata in tqdm(metadatas, "Validating metadata for chromadb...", colour="yellow"):
            for key, value in metadata.items():
                metadata[key] = str(value)
        return metadatas

    @staticmethod
    def prepare_chroma_documents(texts: [str], metadatas: [dict]):
        items = []
        for idx, txt in enumerate(tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")):
            temp = {
                "id": str(uuid.uuid4()),
                "text": txt,
                "vector": generate_chroma_embeddings(text=txt),
                "metadata": metadatas[idx],
            }
            items.append(temp)
        return items

    def overwrite_collection_check(self, collection_name: str):
        if self.config.overwrite and VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            Log.w(f"Deleting existing collection {collection_name}")
            VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)

    """ HELPER to split data into smaller chunks for vector database """
    def __split_docs_into_smaller_chunks(self, docs:[]):
        return self.text_splitter.split_documents(docs)


    @staticmethod
    def delete_collections(*collections:str):
        for collection in collections:
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection)
            except Exception as e:
                Log.e(e)


"""
Raw Text Pipeline...

def store_text_in_vector_db(self, text, metadata, collection_name) -> bool:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=app.state.config.CHUNK_SIZE,
        chunk_overlap=app.state.config.CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = text_splitter.create_documents([text], metadatas=[metadata])
    return self.run_pipeline(docs=docs, collection_name=collection_name)
"""