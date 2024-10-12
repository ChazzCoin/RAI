import json

from F import DICT


from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument
from F.LOG import Log
Log = Log("JSONDataLoader")

class JSONDataLoader:
    cache: [RaiLoaderDocument] = None
    def __init__(self, file_path: str, metadata={ 'image':'' }):
        self.file_path = file_path
        self.metadata = metadata if not None else {'image': ''}

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
            return self.cache

        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=data)
        self.cache = RaiLoaderDocument(page_content=data_string, metadata=self.metadata)
        return self.cache