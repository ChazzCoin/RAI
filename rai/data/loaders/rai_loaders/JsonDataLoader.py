import json

from F import DICT


from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument
from F.LOG import Log
Log = Log("JSONDataLoader")


def ensure_string(data):
    """
    Recursively ensure that all values are strings.
    If a value is None, convert it to the literal string "null".
    """
    if data is None:
        return "null"
    elif isinstance(data, dict):
        # Convert keys and values to strings, with None replaced by "null"
        return {str(k): ensure_string(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Convert each list item to a string, replacing None with "null"
        return [ensure_string(item) for item in data]
    elif isinstance(data, (int, float, bool)):
        # Convert numbers/bools directly to strings
        return str(data)
    # For strings or anything else, just ensure it's a string
    return str(data)

class JSONDataLoader:
    cache: [RaiLoaderDocument] = None
    is_file: bool = False
    json_data: [{}] = None

    def __init__(self, file_path: str=None, json_objects=None, metadata=None):
        if file_path:
            self.file_path = file_path
            self.is_file = True
        elif json_objects:
            if type(json_objects) not in [list, tuple]:
                self.json_data = [json_objects]
            else:
                self.json_data = json_objects

        self.metadata = metadata if metadata is not None else {'image': ''}

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
            return self.cache

        if not self.is_file:
            r = []
            for item in self.json_data:
                cleaned_item = ensure_string(item)
                str_content = json.dumps(cleaned_item, ensure_ascii=False)
                # The final string might contain "null" if it was None before, which is intended
                doc = RaiLoaderDocument(page_content=str_content, metadata=self.metadata)
                r.append(doc)
            self.cache = r
            return self.cache

        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Sanitize metadata as well
        self.metadata = ensure_string(self.metadata)
        # Try to get a main text content field
        data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=data)
        if not data_string:
            # If no direct string found, we handle the data as either a list/tuple or a single object.
            if isinstance(data, (list, tuple)):
                r = []
                for item in data:
                    cleaned_item = ensure_string(item)
                    str_content = json.dumps(cleaned_item, ensure_ascii=False)
                    # The final string might contain "null" if it was None before, which is intended
                    doc = RaiLoaderDocument(page_content=str_content, metadata=self.metadata)
                    r.append(doc)
                self.cache = r
                return self.cache
            else:
                cleaned_data = ensure_string(data)
                str_content = json.dumps(cleaned_data, ensure_ascii=False)
                doc = RaiLoaderDocument(page_content=str_content, metadata=self.metadata)
                self.cache = [doc]
                return self.cache
        else:
            # Ensure the retrieved content is also sanitized
            cleaned_data = ensure_string(data_string)
            str_content = json.dumps(cleaned_data, ensure_ascii=False)
            doc = RaiLoaderDocument(page_content=str_content, metadata=self.metadata)
            self.cache = [doc]
            return self.cache


# class JSONDataLoader:
#     cache: [RaiLoaderDocument] = None
#     def __init__(self, file_path: str, metadata={ 'image':'' }):
#         self.file_path = file_path
#         self.metadata = metadata if not None else {'image': ''}
#
#     def load(self):
#         if self.cache:
#             Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
#             return self.cache
#
#         with open(self.file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         data_string = DICT.get_any(keys={"content", "text", "page", "page_content"}, dic=data)
#         if not data_string:
#             r = []
#             for item in data:
#                 temp = RaiLoaderDocument(page_content=str(item).replace("{", "").replace("}", ""), metadata=self.metadata)
#                 r.append(temp)
#             self.cache = r
#             return self.cache
#         self.cache = [RaiLoaderDocument(page_content=data_string, metadata=self.metadata)]
#         return self.cache