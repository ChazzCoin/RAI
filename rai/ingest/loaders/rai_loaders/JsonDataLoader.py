import json
from F import DICT

from rai.ingest.loaders.rai_loaders.BaseLoad import RaiBaseLoader, IngestLoaderDocument
from rai.ingest.loaders.rai_loaders.Utils import ensure_string
from F.LOG import Log

from rai.raigents.base.BaseLoaders import register_loader

Log = Log("JSONDataLoader")


@register_loader(name="json")
class JSONDataLoader(RaiBaseLoader):
    cache: [IngestLoaderDocument] = None
    is_file: bool = False
    json_data: [{}] = None

    def __init__(self, file_path: str = None, json_objects=None, metadata=None):
        super().__init__(file_path, metadata)
        if file_path:
            self.file_path = file_path
            self.is_file = True
        elif json_objects:
            # Ensure json_data is always a list
            if not isinstance(json_objects, (list, tuple)):
                self.json_data = [json_objects]
            else:
                self.json_data = json_objects

        self.metadata = metadata if metadata is not None else {'image': ''}

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {getattr(self, 'file_path', None)} ]")
            return self.cache

        # -----------------------------
        # 1) Handle the NO-FILE scenario
        # -----------------------------
        if not self.is_file:
            # Sanitize the top-level metadata as well
            self.metadata = ensure_string(self.metadata)
            # Attempt to pull out a main text field if it exists
            data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=self.json_data)
            if data_string:
                return self.parse_string(data_string)
            else:
                return self.parse_string(self.json_data)

        # -----------------------------
        # 2) Handle the FILE scenario
        # -----------------------------
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Sanitize the top-level metadata as well
        self.metadata = ensure_string(self.metadata)
        # Attempt to pull out a main text field if it exists
        data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=data)
        if data_string: return self.parse_string(data_string)
        else: return self.parse_json(data)

    def parse_string(self, data):
        # If we found a direct content field, treat it as a single object
        cleaned_data = ensure_string(data)
        str_content = json.dumps(cleaned_data, ensure_ascii=False)
        doc = IngestLoaderDocument(page_content=str_content, metadata=self.metadata)
        self.cache = [doc]
        return self.cache

    def parse_json(self, data):
        if isinstance(data, (list, tuple)):
            # If it's a list, handle similarly as above
            if len(data) == 1:
                # Just one item in the list
                cleaned_data = ensure_string(data[0])
                str_content = json.dumps(cleaned_data, ensure_ascii=False)
                doc = IngestLoaderDocument(page_content=str_content, metadata=self.metadata)
                self.cache = [doc]
                return self.cache
            # Otherwise, multiple items
            all_keys_list = []
            for obj in data:
                if isinstance(obj, dict):
                    all_keys_list.append(set(obj.keys()))
                else:
                    all_keys_list.append(set())
            r = []
            for i, item in enumerate(data):
                cleaned_item = ensure_string(item)

                for key, value in cleaned_item.items():
                    self.metadata["parent"] = str(key)
                    self.metadata["children"] = str(all_keys_list)
                    for item in value:
                        str_content = json.dumps(item, ensure_ascii=False)
                        doc = IngestLoaderDocument(page_content=str_content, metadata=self.metadata)
                        r.append(doc)
            self.cache = r
            return self.cache
        else:
            # Single dictionary
            cleaned_data = ensure_string(data)
            str_content = json.dumps(cleaned_data, ensure_ascii=False)
            doc = IngestLoaderDocument(page_content=str_content, metadata=self.metadata)
            self.cache = [doc]
            return self.cache