from typing import List, Any
from F.LOG import Log
from langchain_core.document_loaders import BaseLoader

Log = Log("RaiLoaderDocument")

class RaiLoaderDocument:
    page_content:str
    metadata:dict

    def __init__(self, page_content: str, metadata:dict={ 'image':'' }) -> None:
        self.page_content = page_content
        self.metadata = metadata if not None else { 'image': '' }

    @staticmethod
    def generate_documents(items:[str], metadata:dict={ 'image':'' }):
        docs = []
        for item in items:
            docs.append(RaiLoaderDocument(item, metadata))
        return docs


class RaiBaseLoader(BaseLoader):
    file_path = ""
    metadata = { 'image':'' }
    data = None
    cache: [RaiLoaderDocument] = None

    def __init__(self, file_path: str, metadata: dict = {'image': ''}):
        self.file_path = file_path
        self.metadata = metadata if not None else { 'image': '' }

    def get_subset(self, batches: int) -> List[Any]:
        batched_data = []
        if not self.data and not self.cache: self.load()
        if len(self.cache) < batches:
            batches = len(self.cache)
        for batch in range(batches):
            item: RaiLoaderDocument = self.cache[batch]
            batched_data.append(item.page_content)
        return batched_data

    def is_empty(self):
        if not self.data:
            return True
        return False

    def should_fallback(self):
        if not self.data:
            Log.w("No Vision Data. Falling Back.")
            return True
        Log.w("Vision Found Data.")
        return False

    @staticmethod
    def verify_loader_data(loader: BaseLoader) -> bool:
        try:
            # Attempt to load data from the provided loader
            data = loader.load()
            # Check if data is not None, is a list, and has valid contents
            if data is None:
                return False
            if not isinstance(data, list):
                return False
            if len(data) == 0:
                return False
            # If all checks pass, return True
            return True
        except Exception as e:
            # If any exception occurs, log it if needed and return False
            # You could add logging here for better traceability in production
            Log.w("Failed Loader Validation", e)
            return False