
from F.LOG import Log
from langchain_core.document_loaders import BaseLoader

from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument

Log = Log("RawTextDataLoader")


class RawTextDataLoader(BaseLoader):
    def __init__(self, raw_text: str, metadata={ 'image':'' }):
        self.data = raw_text
        self.metadata = metadata if not None else { 'image': '' }

    def load(self):
        return [RaiLoaderDocument(page_content=self.data, metadata=self.metadata)]