import os

import docx
from F.LOG import Log
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.document_loaders import BaseLoader

from rai.data.loaders import verify_loader_data
from rai.data.loaders.rai_loaders.LastResortDataLoader import LastResortDataLoader
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument
from rai.data.loaders.rai_loaders.RaiMetadataLoader import DEFAULT_METADATA
from rai.data.loaders.rai_loaders.VisionDataLoader import VisionDataLoader

Log = Log("WordDocDataLoader")

class WordDocDataLoader(BaseLoader):
    cache: [RaiLoaderDocument] = None
    def __init__(self, file_path: str, metadata:dict=DEFAULT_METADATA):
        self.file_path = file_path
        self.metadata = metadata
        self._validate_file_path()

    def _validate_file_path(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not self.file_path.endswith('.docx'):
            raise ValueError("Unsupported file type. Only DOCX files are allowed.")

    def load(self) -> [str]:
        """
        Loads and extracts the text from the DOCX file.
        The output is a list of formatted strings representing each paragraph,
        useful for embeddings, querying, and AI processing.
        """
        try:
            if self.cache:
                Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
                return self.cache
            document = docx.Document(self.file_path)
            formatted_paragraphs = self.format_docx(document)
            if formatted_paragraphs:
                Log.i(f"Docx Success: [ {self.file_path} ]")
                self.cache = RaiLoaderDocument.generate_documents(formatted_paragraphs, metadata=self.metadata)
                return self.cache
            else:
                raise ValueError("DOCX is empty or could not be processed.")
        except Exception as e:
            # Fallback to VisionDataLoader if the primary method fails
            Log.w(f"Docx Failed, Falling back to Vision: [ {self.file_path} ]")
            loader = VisionDataLoader(self.file_path, metadata=self.metadata)
            if loader.should_fallback():
                # Fallback to PyPDFLoader if VisionDataLoader is empty
                loader = Docx2txtLoader(self.file_path)
                if not verify_loader_data(loader):
                    # Fallback to LastResortLoader if all else fails
                    Log.w("WordDocLoader Failed, last resorting.", e)
                    loader = LastResortDataLoader(self.file_path, metadata=self.metadata)
            self.cache = loader.load()
            return self.cache
    @staticmethod
    def format_docx(document: docx.Document) -> [str]:
        """
        Formats the DOCX content into a list of strings,
        each representing a paragraph in a consistent and structured format.
        """
        Log.i("Formatting Word Doc...")
        formatted_paragraphs = []
        for para_num, paragraph in enumerate(document.paragraphs, start=1):
            if paragraph.text.strip():
                formatted_paragraphs.append(f"Paragraph {para_num}: {paragraph.text.strip()}")

        return formatted_paragraphs