import json
import os

from F import DICT
from F.LOG import Log
from jsonlines import jsonlines
from langchain_core.document_loaders import BaseLoader

from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument

Log = Log("JSONLDataLoader")

class JSONLDataLoader(BaseLoader):
    cache: [RaiLoaderDocument] = None
    def __init__(self, file_path: str, metadata={ 'image':'' }):
        self.file_path = file_path
        self.metadata = metadata if not None else { 'image': '' }

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
            return self.cache
        self.cache = []
        try:
            with jsonlines.open(self.file_path) as reader:
                for obj in reader:
                    data_string = DICT.get_any(keys=["content", "text", "page", "page_content"], dic=obj)
                    self.cache.append(RaiLoaderDocument(page_content=data_string, metadata=self.metadata))
        except Exception as e:
            Log.e(e)
            self.cache = []
        return self.cache

    @staticmethod
    def load_file(file:str):
        objs = []
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        objs.append(item)
                    except json.JSONDecodeError:
                        continue
            return objs
        else: return objs
    @staticmethod
    def save_file(data: dict, output_file:str):
        with open(output_file, 'a', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')