import os

import PyPDF2
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.document_loaders import BaseLoader

from F.LOG import Log

from rai.data.loaders import verify_loader_data
from rai.data.loaders.rai_loaders.LastResortDataLoader import LastResortDataLoader
from rai.data.loaders.rai_loaders.VisionDataLoader import VisionDataLoader

Log = Log("PdfDataLoader")

class PdfDataLoader(BaseLoader):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._validate_file_path()

    def _validate_file_path(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not self.file_path.endswith('.pdf'):
            raise ValueError("Unsupported file type. Only PDF files are allowed.")

    def load(self) -> [str]:
        """
        Loads and extracts the text from the PDF file.
        The output is a list of formatted strings representing each page,
        useful for embeddings, querying, and AI processing.
        """
        try:

            with open(self.file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                formatted_pages = self.format_pdf(reader)
                if formatted_pages:
                    Log.i(f"PyPDF2 Reader Success: [ {self.file_path} ]")
                    return formatted_pages
                else:
                    raise ValueError("PDF is empty or could not be processed.")
        except Exception as e:
            # Fallback to VisionDataLoader if the primary method fails
            Log.w("PyPDF2 Failed, falling back to Vision.", e)
            loader = VisionDataLoader(self.file_path)
            if loader.should_fallback():
                # Fallback to PyPDFLoader if VisionDataLoader is empty
                loader = PyPDFLoader(self.file_path, extract_images=True)
                if not verify_loader_data(loader):
                    # Fallback to LastResortLoader if all else fails
                    loader = LastResortDataLoader(self.file_path)
            return loader.load()

    @staticmethod
    def format_pdf(reader: PyPDF2.PdfReader) -> [str]:
        """
        Formats the PDF content into a list of strings,
        each representing a page in a consistent and structured format.
        """
        Log.i("Formatting Pdf...")
        formatted_pages = []
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_text = page.extract_text() if page.extract_text() else ""
            formatted_pages.append(f"Page {page_num + 1}: {page_text}")

        return formatted_pages