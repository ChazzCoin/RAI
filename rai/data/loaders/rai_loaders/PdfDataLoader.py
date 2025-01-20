import os
import PyPDF2
from langchain_community.document_loaders import PDFMinerLoader, PDFPlumberLoader

from F.LOG import Log

from rai.base.BaseLoaders import register_loader
from rai.data.loaders.rai_loaders.BaseLoad import RaiLoaderDocument
from rai.data.parsers.Pdf_v2 import RaiPdfMiner

Log = Log("PdfDataLoader")

def safe(func):
    try:
        return func()
    except Exception as e:
        print(e)
        return None

@register_loader(name="pdf")
class PdfDataLoader(RaiPdfMiner):
    fpdf = None
    ocr = None
    def __init__(self, file_path: str):
        super().__init__(file_path)
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

    def load(self) -> [RaiLoaderDocument]:
        if self.cache: return self.cache
        return self.run()

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