import json
import time
import uuid

from F import LIST, DICT
from F.CLASS import Flass
from rai import app
from F.LOG import Log
from tqdm import tqdm

from rai.agents.RaiAgents import AgentRegistry, AgentCategorizer
from rai.agents.Tools import RaiFunctionCategories, YouthSoccerWebsiteCategories
from rai.assistant.connectors import RaiAi
from rai.data import RaiPath
from rai.internal.connectors import VECTOR_DB_CLIENT
from rai.assistant.openai_client import generate_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from rai.data.loaders import RaiDataLoaders
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiBaseLoader
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader

Log = Log("RaiFileExtractor")

ai = RaiAi()

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
    single_run: bool = False
    category_context: str = "Youth Soccer Club"
    primary_functions = RaiFunctionCategories
    secondary_functions = YouthSoccerWebsiteCategories

class RaiFileExtractor:
    config = RaiConfig()
    file_to_import_by_collection: {str:list} = {}
    file_to_import_count = 0
    cached_metadata = None

    pending = {}
    success = {}
    failed = {}

    current_file = ""

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

    def __run_pipeline(self, docs:[]=None, loader:RaiBaseLoader=None):
        if not docs: docs = loader.load()
        if self.config.split_documents:
            docs = self.__split_docs_into_smaller_chunks(docs)
        if self.config.pipeline.lower() == "chroma": return self.sort_for_chroma(docs)
        elif self.config.pipeline.lower() == "print": return self.to_printer(docs)

    def to_printer(self, docs:[]):
        Log.w(f"Printing Docs for Collection: [ {self.config.file_collection_name} ]")
        time.sleep(1)
        count = 0
        for d in docs:
            print(f"Record [ {count} ] [ {self.config.file_collection_name} ]:\n {d.page_content}")
            count += 1
            time.sleep(1)

    def sort_for_chroma(self, docs:[]):
        texts = self.get_texts(docs)
        metadata = self.prepare_metadatas(docs)
        items = self.prepare_chroma_documents(texts, metadata)
        cnames = self.get_collection_category_name(' '.join(texts))
        for c in cnames: self.add_to_pending(c, items)

    def to_chroma(self):
        for collection,items in self.pending.items():
            current_name = f"{self.config.collection_prefix}.{collection}"
            Log.i(f"importing [ {len(items)} ] docs in [ {current_name} ]")
            try:
                self.overwrite_collection_check(current_name)
                VECTOR_DB_CLIENT.insert(
                    collection_name=current_name,
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
        value_old = DICT.get(collection, self.pending, [])
        value_new = LIST.merge_lists(value_old, items)
        self.success[collection] = LIST.flatten(value_new)
    def add_to_failed(self, collection, items):
        value_old = DICT.get(collection, self.pending, [])
        value_new = LIST.merge_lists(value_old, items)
        self.failed[collection] = LIST.flatten(value_new)


    def get_collection_category_name(self, data):
        categorizer = AgentCategorizer()
        results1 = categorizer.run(data, self.config.category_context, self.config.primary_functions)
        results2 = categorizer.run(data, self.config.category_context, self.config.secondary_functions)
        return LIST.remove_duplicates(LIST.merge_lists(results1, results2))

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
                if type(meta) in [str]:
                    meta_dict = json.loads(meta)
                else:
                    meta_dict = meta
                for key,value in meta_dict.items():
                    final_meta[str(key)] = str(value)
                final_meta["file"] = str(self.current_file)
                return final_meta
            else:
                metadatas = RaiFileExtractor.get_metadatas(docs)
            for key,value in LIST.get(0, metadatas, {}).items():
                final_meta[str(key)] = str(value)
            final_meta["file"] = str(self.current_file)
            return final_meta
        except Exception as e:
            Log.w(e)
            return {}
    @staticmethod
    def prepare_chroma_documents(texts: [str], metadata: dict):
        items = []
        for idx, txt in enumerate(tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")):
            temp = {
                "id": f"{str(uuid.uuid4())}:{str(idx)}",
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


class RaiFileManager:
    """
    Responsible for:
      - Importing a directory (recursively) for file paths.
      - Loading files and extracting documents from them.
      - Splitting documents into smaller chunks if configured.
      - Returning those prepared docs so that another class
        (RaiChromaDBDocumentManager) can handle the storage into Chroma.
    """

    def __init__(self, config: RaiConfig):
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