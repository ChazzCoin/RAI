import os
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyPDFLoader, PDFMinerLoader, PDFPlumberLoader

from F.LOG import Log

from rai.data.loaders import verify_loader_data
from rai.data.loaders.rai_loaders.LastResortDataLoader import LastResortDataLoader
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument, RaiBaseLoader
from rai.data.loaders.rai_loaders.RaiMetadataLoader import DEFAULT_METADATA
from rai.data.loaders.rai_loaders.VisionDataLoader import VisionDataLoader

Log = Log("PdfDataLoader")

def safe(func):
    try:
        return func()
    except Exception as e:
        print(e)
        return None

class PdfDataLoader(RaiBaseLoader):

    def __init__(self, file_path: str, metadata=DEFAULT_METADATA):
        super().__init__(file_path, metadata)
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
            loader = None
            if self.cache:
                Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
                return self.cache
            # Convert PDF pages to images
            images = convert_from_path(self.file_path)
            # Extract text from each image
            loader = []
            for image in images:
                contents = pytesseract.image_to_string(image)
                loader.append(RaiLoaderDocument(page_content=contents))
            self.cache = loader
            return self.cache

        except Exception as e:
            # Fallback to VisionDataLoader if the primary method fails
            Log.w("PyPDF2 Failed, falling back to Vision.", e)
            loader = PDFPlumberLoader(self.file_path)
            if not loader:
                loader = PDFMinerLoader(self.file_path)
            if loader:
                self.cache = loader.load()
            return self.cache

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