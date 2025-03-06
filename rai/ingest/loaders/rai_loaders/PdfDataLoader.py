import os
from langchain_community.document_loaders import PDFMinerLoader

from F.LOG import Log

from rai.agentic.BaseLoaders_dep import register_loader

Log = Log("PdfDataLoader")

def safe(func):
    try:
        return func()
    except Exception as e:
        print(e)
        return None

@register_loader(name="pdf")
class PdfDataLoader:
    file_path = None

    fpdf = None
    ocr = None
    def __init__(self, file_path: str):
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
        loader = PDFMinerLoader(self.file_path)
        if loader:
            self.cache = loader
        return self.cache

    def load(self) -> ['RaiLoaderDocument']:
        if self.cache: return self.cache
        return self.run()

