import os
import shutil
import stat
from langchain_community.document_loaders import (
    BSHTMLLoader,
    OutlookMessageLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredMarkdownLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
)
from langchain_core.document_loaders import BaseLoader
from rai.data import RaiPath
from F.LOG import Log

from rai.data.loaders.rai_loaders.JsonDataLoader import JSONDataLoader
from rai.data.loaders.rai_loaders.JsonlDataLoader import JSONLDataLoader
from rai.data.loaders.rai_loaders.LastResortDataLoader import LastResortDataLoader
from rai.data.loaders.rai_loaders.PdfDataLoader import PdfDataLoader
from rai.data.loaders.rai_loaders.PowerPointDataLoader import PowerPointDataLoader
from rai.data.loaders.rai_loaders.TableDataLoader import TableDataLoader
from rai.data.loaders.rai_loaders.WordDocDataLoader import WordDocDataLoader

Log = Log("RaiDataLoader")

DEFAULT_CONTENT = "This data is unknown at this time."

class RaiDataLoader:
    file:str = None
    loader: BaseLoader = None
    """ -> private DATA LOADER HELPER <- """

    def __init__(self, file):
        self.file = file
        self.loader = self.get_loader(file)

    @staticmethod
    def get_loader(file_path: str) -> BaseLoader:
        rai_file = RaiPath(file_path)
        file_ext = rai_file.ext_type
        Log.w(f"Finding Dataloader for Ext: [ {file_ext} ]...")
        try:
            if file_ext == "pdf":
                loader = PdfDataLoader(file_path)
            elif file_ext in ["csv", "xls", "xlsx"]:
                loader = TableDataLoader(file_path)
            elif file_ext == "jsonl":
                loader = JSONLDataLoader(file_path)
            elif file_ext == "json":
                loader = JSONDataLoader(file_path)
            elif file_ext == "rst":
                loader = UnstructuredRSTLoader(file_path, mode="elements")
            elif file_ext == "xml":
                loader = UnstructuredXMLLoader(file_path)
            elif file_ext in ["htm", "html"]:
                loader = BSHTMLLoader(file_path, open_encoding="unicode_escape")
            elif file_ext == "md":
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_ext == "epub":
                loader = UnstructuredEPubLoader(file_path)
            elif file_ext == "docx":
                loader = WordDocDataLoader(file_path)
            elif file_ext in ["ppt", "pptx"]:
                loader = PowerPointDataLoader(file_path)
            elif file_ext == "msg":
                loader = OutlookMessageLoader(file_path)
            elif file_ext == "txt":
                loader = LastResortDataLoader(file_path)
            elif file_ext in known_source_ext:
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TextLoader(file_path, autodetect_encoding=True)
        except Exception as e:
            Log.w("Failed, falling back to original read file.", e)
            loader = None
        """ Fallback Intake Method """
        verification = RaiDataLoader.verify_loader_data(loader)
        if not verification:
            loader = LastResortDataLoader(file_path)
        return loader

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


known_source_ext = [
            "go",
            "py",
            "java",
            "sh",
            "bat",
            "ps1",
            "cmd",
            "js",
            "ts",
            "css",
            "cpp",
            "hpp",
            "h",
            "c",
            "cs",
            "sql",
            "log",
            "ini",
            "pl",
            "pm",
            "r",
            "dart",
            "dockerfile",
            "env",
            "php",
            "hs",
            "hsc",
            "lua",
            "nginxconf",
            "conf",
            "m",
            "mm",
            "plsql",
            "perl",
            "rb",
            "rs",
            "db2",
            "scala",
            "bash",
            "swift",
            "vue",
            "svelte",
            "msg",
            "ex",
            "exs",
            "erl",
            "tsx",
            "jsx",
            "hs",
            "lhs",
        ]