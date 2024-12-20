import json
import time
import uuid

from F import LIST
from F.CLASS import Flass
from rai import app
from F.LOG import Log
from tqdm import tqdm
from rai.data import RaiPath
from rai.internal.connectors import VECTOR_DB_CLIENT
from rai.assistant.openai_client import generate_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from rai.data.loaders import RaiDataLoaders
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiBaseLoader
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader

Log = Log("RaiFileExtractor")

class RaiConfig(Flass):
    pipeline: str = "print"
    collection_prefix: str = None
    file_collection_name: str = ""
    base_path: RaiPath = None
    overwrite: bool = False
    split_documents: bool = False
    metadatas: [dict] = None
    generate_ai_metadata: bool = False
    meta_loader: RaiMetadataLoader = RaiMetadataLoader()
    text_splitter: RecursiveCharacterTextSplitter = None

class RaiFileExtractor:
    config = RaiConfig()
    file_to_import_by_collection: {str:list} = {}
    file_to_import_count = 0
    cached_metadata = None

    class Pipelines:
        PRINT = "print"
        CHROMA = "chroma"

    def __init__(self, config: RaiConfig):
        self.config = config
        Log.w("Chunk Overlap:", app.state.config.CHUNK_OVERLAP)
        Log.w("Chunk Size:", app.state.config.CHUNK_SIZE)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )

    def import_directory(self, directory_path: str = None):
        if directory_path is not None:
            self.config.base_path = RaiPath(directory_path)

        Log.i(f"Preparing Files for Import: [ {self.config.base_path} ]")
        self.file_to_import_count = 0
        self.file_to_import = []
        # Recursively traverse the directory tree starting from base_path
        for file_path in self.config.base_path.path.rglob('*'):
            if file_path.is_file():
                self.file_to_import.append(file_path)
                self.file_to_import_count += 1

        # Proceed with the import process
        Log.s(f"Starting Import: Total [ {self.file_to_import_count} ]")
        for file in self.file_to_import:
            if str(file).endswith('.DS_Store'):
                continue
            """
                Handle Naming...
                csv, xlsx need to be their own collection.
            """
            self.import_file(file_path=file)
        Log.s(f"Finished Importing Files: Total [ {self.file_to_import_count} ]")
        return True

    def import_file(self, file_path:str):
        try:
            if file_path is not None:
                file_path = RaiPath(file_path)
                self.config.file_collection_name = f"{self.config.collection_prefix}.{RaiPath.sanitize_file_name_for_chromadb(file_path)}"
            Log.i(f"Processing: [ {file_path} ] for Collection: [ {self.config.file_collection_name} ]")
            self.cached_metadata = None
            loader = RaiDataLoaders.RaiDataLoader(file_path, meta_loader=self.config.meta_loader).loader
            try:
                result = self.__run_pipeline(loader=loader)
                if result: Log.s(f"Finished Importing: [ {file_path} ]")
            except Exception as e: Log.w(f"Error importing file '{file_path}' to Chroma DB: {e}")
        except Exception as e: Log.w(f"Error importing file '{file_path}': {e}")

    def __run_pipeline(self, docs:[]=None, loader:RaiBaseLoader=None):
        if not docs: docs = loader.load()
        if self.config.split_documents:
            docs = self.__split_docs_into_smaller_chunks(docs)
        if self.config.pipeline.lower() == "chroma": return self.to_chroma(docs)
        elif self.config.pipeline.lower() == "print": return self.to_printer(docs)

    def to_printer(self, docs:[]):
        Log.w(f"Printing Docs for Collection: [ {self.config.file_collection_name} ]")
        time.sleep(1)
        count = 0
        for d in docs:
            print(f"Record [ {count} ] [ {self.config.file_collection_name} ]:\n {d.page_content}")
            count += 1
            time.sleep(1)

    def to_chroma(self, docs:[]):
        Log.i(f"importing [ {len(docs)} ] docs in [ {self.config.file_collection_name} ]")
        texts = self.get_texts(docs)
        metadata = self.prepare_metadatas(docs)
        items = self.prepare_chroma_documents(texts, metadata)
        try:
            self.overwrite_collection_check(self.config.file_collection_name)
            VECTOR_DB_CLIENT.insert(
                collection_name=self.config.file_collection_name,
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
        final_meta = {}
        try:
            if self.config.generate_ai_metadata:
                meta = RaiMetadataLoader().ai_genny(raiDocs=docs)
                meta_dict = json.loads(meta)
                for key,value in meta_dict.items():
                    final_meta[str(key)] = str(value)
                return final_meta
            else:
                metadatas = RaiFileExtractor.get_metadatas(docs)
            for key,value in LIST.get(0, metadatas, {}).items():
                final_meta[str(key)] = str(value)
            return final_meta
        except Exception as e:
            Log.w(e)
            return {}

    @staticmethod
    def prepare_chroma_documents(texts: [str], metadata: dict):
        items = []
        for idx, txt in enumerate(tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")):
            temp = {
                "id": str(idx),
                "text": txt,
                "vector": generate_embeddings(text=txt),
                "metadata": metadata,
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

    @staticmethod
    def get_all_from_collection(collection: str):
        try:
            VECTOR_DB_CLIENT.get(collection_name=collection)
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