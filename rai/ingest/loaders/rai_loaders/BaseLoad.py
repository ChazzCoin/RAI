from langchain_core.document_loaders import BaseLoader
from typing import List

from F import LIST
from F.LOG import Log

from rai.ingest.IngestModels import IngestPage
from rai.ingest.utilities.DataUtilities import ensure_metadata_is_string_for_chroma
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.raigents.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.raigents.base.BaseTextAgents.BaseTextFormats import RaiMetadata

Log = Log("RaiLoaderDocument")

class IngestLoaderDocument:
    page_content:str
    metadata:dict

    def __init__(self, page_content: str, metadata:dict={ 'image':'' }) -> None:
        self.page_content = page_content
        self.metadata = metadata if not None else { 'image': '' }

    @staticmethod
    def generate_documents(items:[str], metadata:dict={ 'image':'' }):
        docs = []
        for item in items:
            docs.append(IngestLoaderDocument(item, metadata))
        return docs

class RaiBaseLoader(BaseLoader):
    file_path = ""
    metadata = { 'image':'' }
    data = None
    cache: [IngestLoaderDocument] = None

    def __init__(self, file_path: str, metadata: dict = {'image': ''}):
        self.file_path = file_path
        self.metadata = metadata if not None else { 'image': '' }

    @staticmethod
    def verify_loader_data(loader: BaseLoader) -> bool:
        try:
            data = loader.load()
            if data is None: return False
            if not isinstance(data, list): return False
            if len(data) == 0: return False
            return True
        except Exception as e:
            # If any exception occurs, log it if needed and return False
            # You could add logging here for better traceability in production
            print("Failed Loader Validation", e)
            return False



class RaiDocCreator(RaiBaseLoader, TextProcessor):
    cache:[] = []
    documents: List['IngestLoaderDocument'] = []

    def __init__(self, file_path: str=None):
        super().__init__(file_path)

    def generate_metadata(self, content:str) -> dict:
        Log.i("Generating Metadata.")
        metadata: RaiMetadata = RaiBaseTextAgent.tool(name='metadata', user_prompt=content)
        return metadata.model_dump()

    def are_docs_identical(self, doc1: IngestLoaderDocument, doc2: IngestLoaderDocument) -> bool:
        if self.are_strings_identical(doc1.page_content, doc2.page_content):
            if self.are_dicts_identical(doc1.metadata, doc2.metadata):
                return True
        return False

    def has_doc(self, doc: IngestLoaderDocument) -> bool:
        if doc in self.cache: return True
        for document in self.cache:
            if self.are_docs_identical(document, doc):
                return True
        return False

    def add_doc(self, page_content, metadata):
        content = self.TEXT_CLEANER(str(page_content))
        if not self.string_length_is_within(text=content, max_length=5000):
            contents = self.split_string_by_limit(content, char_limit=5000)
        else: contents = [content]

        for c in contents:
            doc = IngestLoaderDocument(
                page_content=c,
                metadata=ensure_metadata_is_string_for_chroma(metadata)
            )
            if self.has_doc(doc): return
            self.cache.append(doc)

    def to_documents(self, page: IngestPage):
        """ Web Contents Loader """
        Log.i("Creating Content Documents.")
        try:
            page.metadata['collection'] = "pages"
            self.add_doc(page.content, page.metadata)
        except Exception as e:
            print(f"No Content. {e}")
        """ Table Contents Loader """
        Log.i("Creating Table Documents.")
        try:
            page.metadata['collection'] = "tables"
            for tableItem in LIST.flatten(page.table_objs):
                self.add_doc(tableItem, page.metadata)
        except Exception as e:
            print(f"No Tables. {e}")
        """ Events Contents Loader """
        Log.i("Creating Event Documents.")
        try:
            page.metadata['collection'] = "events"
            for eventItem in LIST.flatten(page.events):
                self.add_doc(eventItem, page.metadata)
        except Exception as e:
            print(f"No Events. {e}")

        """ Table Contents Loader """
        Log.i("Creating PDF Content Documents.")
        try:
            page.metadata['collection'] = "pdfs"
            for pdfItem in LIST.flatten(page.pdfs_content):
                self.add_doc(pdfItem, page.metadata)
        except Exception as e:
            print(f"No Pdfs. {e}")
        Log.i("Creating Image Content Documents.")
        try:
            page.metadata['collection'] = "images"
            for imageItem in LIST.flatten(page.images_content):
                self.add_doc(imageItem, page.metadata)
        except Exception as e:
            print(f"No Images. {e}")

        Log.i("Creating Location Content Documents.")
        try:
            page.metadata['collection'] = "locations"
            for locationItem in LIST.flatten(page.locations):
                self.add_doc(locationItem, page.metadata)
        except Exception as e:
            print(f"No Locations. {e}")

        Log.i("Creating Contact Content Documents.")
        try:
            page.metadata['collection'] = "contacts"
            for contactItem in LIST.flatten(page.locations):
                self.add_doc(contactItem, page.metadata)
        except Exception as e:
            print(f"No Contacts. {e}")

        Log.i("Creating Summary Document.")
        try:
            page.metadata['collection'] = "summaries"
            self.add_doc(page.summary, page.metadata)
        except Exception as e:
            print(f"No Summary. {e}")

        Log.i("Creating Context Group Documents.")
        try:
            page.metadata['collection'] = "context_groups"
            for contextGroupItem in LIST.flatten(page.context_groups):
                self.add_doc(contextGroupItem, page.metadata)
        except Exception as e:
            print(f"No Context Groups. {e}")

        Log.i("Creating Line Documents.")
        try:
            page.metadata['collection'] = "lines"
            for lineItems in LIST.flatten(page.lines):
                self.add_doc(lineItems, page.metadata)
        except Exception as e:
            print(f"No Lines. {e}")

        Log.i(f"Document Count: {len(self.cache)}")
