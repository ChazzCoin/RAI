import json
import time
import uuid

from F import LIST, DICT
from F.CLASS import Flass
from rai import app
from F.LOG import Log
from tqdm import tqdm

from rai.assistant.connectors import RaiAi
from rai.data import RaiPath
from rai.data.loaders.rai_loaders.WebLoader import RaiWebCrawler
from rai.internal.connectors import VECTOR_DB_CLIENT
from rai.assistant.openai_client import generate_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from rai.data.loaders import RaiDataLoaders
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader

Log = Log("RaiFileExtractor")

ai = RaiAi()

class RaiDataImportConfig(Flass):
    class Pipelines:
        PRINT = "print"
        CHROMA = "chroma"
    pipeline: str = "print"
    url: str = None
    username: str = None
    password: str = None
    page_limit: int = 100
    collection_prefix: str = None
    collection: str = None
    file_collection_name: str = ""
    base_path: RaiPath = None
    overwrite: bool = False
    split_documents: bool = False
    metadatas: [dict] = None
    generate_metadata: bool = False
    generate_collection_name: bool = False
    meta_loader: RaiMetadataLoader = RaiMetadataLoader()
    text_splitter: RecursiveCharacterTextSplitter = None
    single_run: bool = False


class RaiDataImporter:
    config = RaiDataImportConfig()
    file_to_import_by_collection: {str:list} = {}
    file_to_import_count = 0
    cached_metadata = None

    pending = {}
    success = {}
    failed = {}

    current_file = ""

    @classmethod
    def run(cls, config: RaiDataImportConfig):
        newCls = cls()
        newCls.setup(config)
        if config.url:
            crawler = RaiWebCrawler.pipeline(config.url, config.page_limit, username=config.username, password=config.password)
            newCls.__run_pipeline(loader=crawler)
        if config.base_path:
            newCls.import_directory(config.base_path)
        return newCls

    def setup(self, config: RaiDataImportConfig):
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
        file_to_import = []
        # Recursively traverse the directory tree starting from base_path
        for file_path in self.config.base_path.path.rglob('*'):
            if file_path.is_file():
                file_to_import.append(file_path)
                self.file_to_import_count += 1

        # Proceed with the import process
        Log.s(f"Starting Import: Total [ {self.file_to_import_count} ]")
        for file in file_to_import:
            if str(file).endswith('.DS_Store'):
                continue
            """
                Handle Naming...
                csv, xlsx need to be their own collection.
            """
            self.import_file(file_path=file)
        Log.s(f"Finished Importing Files: Total [ {self.file_to_import_count} ]")
        return self.to_chroma()
    def import_file(self, file_path:str):
        try:
            if file_path is not None:
                file_path = RaiPath(file_path)
            Log.i(f"Processing: [ {file_path} ] for Collection: [ {self.config.file_collection_name} ]")
            self.cached_metadata = None
            self.current_file = file_path
            loader = RaiDataLoaders.RaiDataLoader(file_path, meta_loader=self.config.meta_loader).loader
            try:
                self.__run_pipeline(loader=loader)
                if self.config.single_run: return self.to_chroma()
            except Exception as e: Log.w(f"Error importing file '{file_path}' to Chroma DB: {e}")
        except Exception as e: Log.w(f"Error importing file '{file_path}': {e}")

    def __run_pipeline(self, docs:[]=None, loader=None):
        if not docs: docs = loader.load()
        if self.config.split_documents:
            docs = self.__split_docs_into_smaller_chunks(docs)
        self.sort(docs)
        if self.config.pipeline.lower() == RaiDataImportConfig.Pipelines.CHROMA: return self.to_chroma()
        elif self.config.pipeline.lower() == RaiDataImportConfig.Pipelines.PRINT: return self.to_printer(docs)

    def to_printer(self, docs:[]):
        Log.w(f"Printing Docs for Collection: [ {self.config.file_collection_name} ]")
        time.sleep(1)
        count = 0
        for d in docs:
            print(f"Record [ {count} ] [ {self.config.file_collection_name} ]:\n {d.page_content}")
            count += 1
            time.sleep(1)

    def sort(self, docs: []):
        items:{} = self.prepare_documents(docs=docs)
        for k,v in items.items():
            self.add_to_pending(k, v)

    def to_chroma(self):
        for collection,items in self.pending.items():
            Log.i(f"importing [ {len(items)} ] docs in [ {collection} ]")
            try:
                self.overwrite_collection_check(collection)
                VECTOR_DB_CLIENT.insert(
                    collection_name=collection,
                    items=items,
                )
                self.add_to_success(collection, [self.current_file])
            except Exception as e:
                Log.e(e)
                self.add_to_failed(collection, [self.current_file])
        self.pending = {}
        return self.post_analysis()

    def post_analysis(self):
        print("--SUCCESS--")
        print(self.success.items())
        print("----------")
        print("--FAILED--")
        print(self.failed.items())
        print("----------")

    def add_to_pending(self, collection, items):
        value_old = DICT.get(collection, self.pending, [])
        value_new = LIST.merge_lists(value_old, items)
        self.pending[collection] = LIST.flatten(value_new)
    def add_to_success(self, collection, items):
        value_old = DICT.get(collection, self.success, [])
        value_new = LIST.merge_lists(value_old, items)
        self.success[collection] = LIST.flatten(value_new)
    def add_to_failed(self, collection, items):
        value_old = DICT.get(collection, self.failed, [])
        value_new = LIST.merge_lists(value_old, items)
        self.failed[collection] = LIST.flatten(value_new)

    @staticmethod
    def get_texts(docs: []):
        metadatas = [doc.page_content for doc in docs]
        return metadatas
    @staticmethod
    def get_metadatas(docs: []):
        metadatas = [{**doc.metadata, **({})} for doc in docs]
        return metadatas
    def prepare_documents(self, docs: []):
        items = {}
        for idx, doc in enumerate(tqdm(docs, desc="Preparing Documents for chromadb...", colour="yellow")):
            temp = {
                "id": f"{str(uuid.uuid4())}:{str(idx)}",
                "text": doc.page_content,
                "vector": generate_embeddings(text=doc.page_content),
                "metadata": doc.metadata,
            }
            # Get the collection from doc.metadata, defaulting to 'general'
            collection = doc.metadata.get('collection', 'general')
            # Build the collection key using the configured prefix and collection name
            c = f"{self.config.collection_prefix}.{collection}"
            # Retrieve the current list of items for this collection, or initialize an empty list if none
            temp_items = items.get(c, [])
            temp_items.append(temp)
            items[c] = temp_items  # Save the updated list back to the dictionary.
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
            return VECTOR_DB_CLIENT.get(collection_name=collection)
        except Exception as e:
            Log.e(e)


class RaiFileManager:
    """
    Responsible for:
      - Importing a directory (recursively) for file paths.
      - Loading files and extracting documents from them.
      - Splitting documents into smaller chunks if configured.
      - Returning those prepared docs so that another class
        (RaiChromaDBDocumentManager) can handle the storage into Chroma.
    """

    def __init__(self, config: RaiDataImportConfig):
        self.config = config
        self.file_to_import_count = 0
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=app.state.config.CHUNK_SIZE,
            chunk_overlap=app.state.config.CHUNK_OVERLAP,
            add_start_index=True,
        )
        Log.w("Chunk Overlap:", app.state.config.CHUNK_OVERLAP)
        Log.w("Chunk Size:", app.state.config.CHUNK_SIZE)

    def import_directory(self, directory_path: str = None):
        """
        Recursively traverses a directory to gather file paths.
        Returns a list of all extracted documents from all files.
        """
        if directory_path is not None:
            self.config.base_path = RaiPath(directory_path)

        Log.i(f"Preparing Files for Import: [ {self.config.base_path} ]")
        self.file_to_import_count = 0
        file_to_import = []

        # Recursively traverse the directory tree starting from base_path
        for file_path in self.config.base_path.path.rglob('*'):
            if file_path.is_file():
                # Skip system files (like .DS_Store)
                if str(file_path).endswith('.DS_Store'):
                    continue
                file_to_import.append(file_path)
                self.file_to_import_count += 1

        Log.s(f"Starting Import: Total [ {self.file_to_import_count} ]")
        all_docs = []
        for file_path in file_to_import:
            docs = self.import_file(file_path)
            if docs:
                all_docs.extend(docs)

        Log.s(f"Finished Importing Files: Total [ {self.file_to_import_count} ]")
        return all_docs

    def import_file(self, file_path: str):
        """
        Imports/loads a single file and (optionally) splits it into smaller documents.
        Returns a list of documents for the given file.
        """
        loaded_docs = []
        try:
            rai_path = RaiPath(file_path)
            Log.i(f"Processing: [ {rai_path} ] for Collection: [ {self.config.file_collection_name} ]")

            loader = RaiDataLoaders.RaiDataLoader(rai_path, meta_loader=self.config.meta_loader).loader
            # Actually load the documents
            docs = loader.load()
            if not docs:
                return []

            # Split docs if needed
            if self.config.split_documents:
                docs = self.__split_docs_into_smaller_chunks(docs)

            loaded_docs.extend(docs)

        except Exception as e:
            Log.w(f"Error importing file '{file_path}': {e}")
        return loaded_docs

    def __split_docs_into_smaller_chunks(self, docs: []):
        """
        Helper to split data into smaller chunks for vector database.
        """
        return self.text_splitter.split_documents(docs)