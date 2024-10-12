

from F.LOG import Log
from langchain_core.document_loaders import BaseLoader

from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument
from rai.data.loaders.rai_loaders.RaiMetadataLoader import DEFAULT_METADATA
from rai.data.loaders.rai_loaders.RawTextDataLoader import RawTextDataLoader
from rai.data.extraction.read import read_file

Log = Log("LastResortLoader")
DEFAULT_CONTENT = "This data is unknown at this time."

class LastResortDataLoader(BaseLoader):
    def __init__(self, file_path: str, metadata: dict = DEFAULT_METADATA):
        self.file_path = file_path
        self.metadata = metadata

    def load(self):
        """
        Attempts to read the file using a custom fallback method.
        If successful, it initializes a RawTextLoader with the extracted text.
        If everything fails, returns a valid data structure with a message indicating that the data is unknown.
        """
        try:
            Log.w(f"LastResortDataLoader has been called!: [ {self.file_path} ]")
            raw_text = read_file(self.file_path, enable_vision=False)
            if raw_text:
                loader = RawTextDataLoader(raw_text, metadata=self.metadata)
                return loader.load()
            else:
                raise ValueError("Failed to extract raw text from the file.")
        except Exception as e:
            Log.t("FINAL DATA LOADER FAILURE ALERT! Falling Back: [ This data is unknown at this time. ]", e)
            return [RaiLoaderDocument(page_content=DEFAULT_CONTENT, metadata=DEFAULT_METADATA)]