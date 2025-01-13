import os
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PDFMinerLoader, PDFPlumberLoader

from F.LOG import Log

from rai.data.loaders.rai_loaders.BaseLoad import RaiBaseLoader
from rai.data.parsers.PDF_v1 import FPDF
from rai.data.loaders.rai_loaders.BaseDoc import RaiLoaderDocument
from rai.data.loaders.rai_loaders.RaiMetadataLoader import DEFAULT_METADATA
from rai.internal.registries import RaiRegistry

Log = Log("PdfDataLoader")

def safe(func):
    try:
        return func()
    except Exception as e:
        print(e)
        return None

@RaiRegistry.data_loader(name="pdf")
class PdfDataLoader(RaiBaseLoader):
    fpdf = None
    ocr = None
    def __init__(self, file_path: str, metadata=DEFAULT_METADATA, fpdf=True, ocr=True):
        super().__init__(file_path, metadata)
        self.fpdf = fpdf
        self.ocr = ocr
        self._validate_file_path()

    def _validate_file_path(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not self.file_path.endswith('.pdf'):
            raise ValueError("Unsupported file type. Only PDF files are allowed.")

    def check_length(self, item):
        try:
            if type(item) == str:
                return len(item)
            if type(item) in [list, tuple]:
                count = 0
                for i in item:
                    count += len(i.page_content)
                return count
            return 0
        except Exception as e:
            print(e)
            try:
                return len(item)
            except:
                return 0

    def fallback(self):
        loader = PDFPlumberLoader(self.file_path)
        if not loader:
            loader = PDFMinerLoader(self.file_path)
        if loader:
            self.cache = loader
        return self.cache

    def load(self) -> [str]:
        """
        Loads and extracts the text from the PDF file.
        The output is a list of formatted strings representing each page,
        useful for embeddings, querying, and AI processing.
        """

        def fpdf():
            if not self.fpdf: return []
            loader = []
            try:
                temp = FPDF.extract_text_from_pdf(self.file_path)
                if temp:
                    for item in temp:
                        loader.append(RaiLoaderDocument(page_content=item))
                    return loader
                return None
            except Exception as e:
                print(e)
                return None
        def ocr():
            if not self.ocr: return []
            try:
                # Convert PDF pages to images
                images = convert_from_path(self.file_path)
                # Extract text from each image
                loader = []
                for image in images:
                    contents = pytesseract.image_to_string(image)
                    loader.append(RaiLoaderDocument(page_content=contents))
                return loader if loader else None
            except Exception as e:
                print(e)
                return None
        try:
            loader = None
            if self.cache:
                Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
                return self.cache

            loader1 = fpdf()
            loader2 = ocr()

            if loader1 and loader2:
                if self.check_length(loader1) >= self.check_length(loader2):
                    loader = loader1
                else:
                    loader = loader2
            elif loader1:
                loader = loader1
            elif loader2:
                loader = loader2

            if not loader:
                return self.fallback()

            self.cache = loader
            return self.cache

        except Exception as e:
            Log.w("PyPDF2 Failed, falling back to Vision.", e)
            return self.fallback()

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