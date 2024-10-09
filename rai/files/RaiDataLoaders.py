import json
import os
import shutil
import stat
import time

import jsonlines
from F import DICT
from F.LOG import Log
from langchain_community.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
)
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from dataset.intake.vision import VisionExtractor
from files import read_file
from rai.files import RaiPath
Log = Log("RaiDataLoaders")

class RaiDataLoader:
    loader = None
    """ -> private DATA LOADER HELPER <- """

    def __init__(self, file):
        self.file = file
        self.loader = self.get_loader(file)

    @staticmethod
    def get_loader(file_path: str) -> BaseLoader:
        rai_file = RaiPath(file_path)
        file_ext = rai_file.ext_type
        Log.w(f"Parsing File: [ {rai_file.file_name} ] Ext: [ {file_ext} ] to get matching DataLoader...")
        try:
            if file_ext == "pdf":
                loader = VisionDataLoader(file_path)
                if loader.is_empty():
                    loader = PyPDFLoader(file_path, extract_images=True)
            elif file_ext == "csv":
                loader = CSVLoader(file_path)
            elif file_ext == "jsonl":
                loader = JSONLLoader(file_path)
            elif file_ext == "json":
                loader = JSONLoader(file_path)
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
                loader = VisionDataLoader(file_path)
                if loader.is_empty():
                    loader = Docx2txtLoader(file_path)
            elif file_ext in ["xls", "xlsx"]:
                loader = UnstructuredExcelLoader(file_path)
            elif file_ext in ["ppt", "pptx"]:
                loader = VisionDataLoader(file_path)
                if loader.is_empty():
                    loader = UnstructuredPowerPointLoader(file_path)
            elif file_ext == "msg":
                loader = OutlookMessageLoader(file_path)
            elif file_ext in known_source_ext:
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                loader = TextLoader(file_path, autodetect_encoding=True)
        except Exception as e:
            Log.w("Failed, falling back to original read file.", e)
            raw_text = read_file(file_path)
            loader = RawTextLoader(raw_text)
        return loader

"""
    CUSTOM LOADERS
"""
class RaiLoaderDocument:
    page_content:str
    metadata:dict

    def __init__(self, page_content: str, metadata:dict=None) -> None:
        self.page_content = page_content
        self.metadata = metadata if not None else { 'image': '' }


class RawTextLoader:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text

    def load(self):
        return [RaiLoaderDocument(page_content=self.raw_text)]

class JSONLLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self):
        docs = []
        try:
            with jsonlines.open(self.file_path) as reader:
                for obj in reader:
                    data_string = DICT.get_any(keys=["content", "text", "page", "page_content"], dic=obj)
                    docs.append(RaiLoaderDocument(page_content=data_string, metadata={'ext': 'jsonl'}))
        except Exception as e:
            Log.e(e)
            docs = []
        return docs

class JSONLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=data)
        return RaiLoaderDocument(page_content=data_string, metadata={'ext': 'json'})

class VisionDataLoader:

    def __init__(self, file_path: str, delete_cache=True):
        self.file_path = file_path
        self.data = VisionExtractor(self.file_path).extract(save_images=True)
        if delete_cache:
            self.delete_cached_folder()
            time.sleep(1)

    def delete_cached_folder(self):
        try:
            out = os.path.splitext(self.file_path)[0]
            Log.w(f"Deleting Cached Output Dir: [ {out}_output ]")
            delete_folder(f"{out}_output")
        except Exception as e:
            Log.e(f"Error removing OS: {e}")

    def load(self, load_text=True, load_images=True):
        Log.w("VisionDataLoader [ load() ] has been called.")
        if not load_text and not load_images:
            return []

        filtered_data = []
        for page in self.data:
            content = ""
            image = ""
            if load_text:
                content = page.get('page_content', '')
            if load_images:
                image = { 'image': page.get('image', '') }
            filtered_data.append(RaiLoaderDocument(page_content=content, metadata=image))
        return filtered_data

    def get_pages(self, load_text=True, load_images=True):
        if self.data is None:
            self.load()
        return self.load(load_text, load_images)

    def get_text(self):
        if self.data is None:
            self.load()
        return [page.get('page_content', '') for page in self.data]

    def get_images(self):
        if self.data is None:
            self.load()
        return [page.get('image', '') for page in self.data]

    def get_images_and_text(self):
        if self.data is None:
            self.load()
        return self.data

    def is_empty(self):
        if self.data is None:
            self.load()
        return not bool(self.data)

    def load_d(self):
        if self.data is None:
            self.load()
        documents = []
        for page in self.data:
            page_content = page.get('page_content', '')
            metadata = {'image': page.get('image', '')}
            documents.append(RaiLoaderDocument(page_content=page_content, metadata=metadata))
        return documents

def delete_folder(folder_path):
    """
    Deletes a folder and all its contents.

    Parameters:
    - folder_path (str): The path to the folder to delete.

    Raises:
    - FileNotFoundError: If the folder does not exist.
    - NotADirectoryError: If the specified path is not a directory.
    - PermissionError: If the operation lacks the necessary permissions.
    - OSError: For other OS-related errors.
    """

    # You can configure logging to output to a file or console as needed

    # Verify that the path exists
    if not os.path.exists(folder_path):
        Log.e(f"Folder not found: {folder_path}")
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    # Verify that the path is a directory
    if not os.path.isdir(folder_path):
        Log.e(f"Specified path is not a directory: {folder_path}")
        raise NotADirectoryError(f"Specified path is not a directory: {folder_path}")

    # Handle read-only files on Windows
    def onerror(func, path, exc_info):
        """
        Error handler for shutil.rmtree.

        If the error is due to an access error (read-only file), it attempts to add write permission and retries.
        If the error is for another reason, it re-raises the error.
        """
        import errno
        if not os.access(path, os.W_OK):
            # Attempt to add write permission
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise

    try:
        shutil.rmtree(folder_path, onerror=onerror)
        Log.i(f"Successfully deleted folder and its contents: {folder_path}")
    except Exception as e:
        Log.e(f"Error deleting folder {folder_path}: {e}")
        raise


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