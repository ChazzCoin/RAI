import json
import uuid

from F import DICT, LIST
from F.LOG import Log
from numpy.distutils.command.config import config
from tqdm import tqdm

from rai.agents.RaiAgents import AgentCategorizer
from rai.agents.Tools import RaiFunctionCategories
from rai.assistant.openai_client import generate_embeddings
from rai.data.extraction.RaiFileExtraction import RaiConfig, RaiFileExtractor
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader
from rai.internal.connectors import VECTOR_DB_CLIENT

Log = Log("RaiChromaDBDocumentManager")

class RaiChromaDBDocumentManager:
    """
    Responsible for:
      - Accepting already-loaded (and possibly chunked) documents.
      - Extracting text & metadata.
      - Preparing Chroma-ready document structures.
      - Inserting documents into Chroma.
      - Handling post-insertion analysis (success/fail).
    """
    config: RaiConfig = None
    @classmethod
    def web(cls, prefix, functions):
        config = RaiConfig()
        config.pipeline = RaiFileExtractor.Pipelines.CHROMA
        config.generate_ai_metadata = True
        config.overwrite = False
        config.single_run = True
        config.base_path = None
        config.collection_prefix = prefix
        config.primary_functions = functions
        return cls(config)

    def __init__(self, config: RaiConfig):
        self.config = config
        self.pending = {}
        self.success = {}
        self.failed = {}

    def __sort_for_chroma(self, docs: [], categories: []=None):
        """
        Uses `get_texts` and `prepare_metadatas` to build items for Chroma insertion.
        Groups them by relevant collection categories.
        """
        texts = self.get_texts(docs)
        metadata = self.prepare_metadatas(docs)
        items = self.prepare_chroma_documents(texts, metadata)

        if categories:
            for c in categories:
                self.add_to_pending(c, items)
            return
        cnames = self.get_collection_category_name(' '.join(texts))
        for c in cnames:
            self.add_to_pending(c, items)


    def to_chroma(self, docs: [], categories: []=None):
        """
        Inserts all 'pending' items into Chroma, respecting overwrite rules.
        Clears `pending` once done.
        """
        self.__sort_for_chroma(docs, categories)
        for collection, items in self.pending.items():
            current_name = f"{self.config.collection_prefix}.{collection}"
            Log.i(f"Importing [ {len(items)} ] docs in [ {current_name} ]")
            try:
                self.overwrite_collection_check(current_name)
                VECTOR_DB_CLIENT.insert(
                    collection_name=current_name,
                    items=items,
                )
                self.add_to_success(collection, ["(Collection Insert)"])
            except Exception as e:
                Log.e(e)
                self.add_to_failed(collection, ["(Collection Insert)"])

        self.pending = {}
        return self.post_analysis()

    def post_analysis(self):
        """
        Simple logging/printing of the final success/fail states after insertion.
        """
        print("--SUCCESS--")
        print(self.success.keys())
        print("----------")
        print("--FAILED--")
        print(self.failed.keys())
        print("----------")

    def add_to_pending(self, collection, items):
        old_value = DICT.get(collection, self.pending, [])
        new_value = LIST.merge_lists(old_value, items)
        self.pending[collection] = LIST.flatten(new_value)

    def add_to_success(self, collection, items):
        old_value = DICT.get(collection, self.success, [])
        new_value = LIST.merge_lists(old_value, items)
        self.success[collection] = LIST.flatten(new_value)

    def add_to_failed(self, collection, items):
        old_value = DICT.get(collection, self.failed, [])
        new_value = LIST.merge_lists(old_value, items)
        self.failed[collection] = LIST.flatten(new_value)

    def get_collection_category_name(self, data):
        """
        Example of using an external categorizer to classify text data.
        """
        categorizer = AgentCategorizer()
        return categorizer.run(data, "Youth Soccer Club", self.config.primary_functions)

    @staticmethod
    def get_texts(docs: []):
        return [doc.page_content for doc in docs]

    @staticmethod
    def get_metadatas(docs: []):
        return [{**doc.metadata} for doc in docs]

    def prepare_metadatas(self, docs: []):
        """
        Optionally uses AI to generate advanced metadata, or just reuses doc metadata.
        """
        final_meta = {}
        try:
            if self.config.generate_ai_metadata:
                meta_loader = RaiMetadataLoader()
                meta = meta_loader.ai_genny(raiDocs=docs)
                # Could be string or dict
                meta_dict = json.loads(meta) if isinstance(meta, str) else meta
                for k, v in meta_dict.items():
                    final_meta[str(k)] = str(v)
            else:
                # Use the raw doc metadata
                if docs:
                    doc_meta = self.get_metadatas(docs)[0]
                    for k, v in doc_meta.items():
                        final_meta[str(k)] = str(v)
            return final_meta
        except Exception as e:
            Log.w(e)
            return {}

    @staticmethod
    def prepare_chroma_documents(texts: [str], metadata: dict):
        """
        Builds the final dictionary structure that Chroma typically expects.
        """
        items = []
        for idx, txt in enumerate(
            tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")
        ):
            items.append({
                "id": f"{str(uuid.uuid4())}:{str(idx)}",
                "text": txt,
                "vector": generate_embeddings(text=txt),
                "metadata": metadata,
            })
        return items

    def overwrite_collection_check(self, collection_name: str):
        """
        If config.overwrite is True, delete the existing collection in Chroma before inserting.
        """
        if self.config.overwrite and VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            Log.w(f"Deleting existing collection {collection_name}")
            VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)

    @staticmethod
    def delete_collections(*collections: str):
        """
        Helper to delete multiple collections by name.
        """
        for collection in collections:
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection)
            except Exception as e:
                Log.e(e)

    @staticmethod
    def get_all_from_collection(collection: str):
        """
        Example helper to fetch all items from a specific collection in Chroma.
        """
        try:
            VECTOR_DB_CLIENT.get(collection_name=collection)
        except Exception as e:
            Log.e(e)
