

from F.LOG import Log
Log = Log("RaiMetadataLoader")

DEFAULT_METADATA = {
    'image':''
}


class RaiMetadataLoader:
    file:str
    metadata:dict = DEFAULT_METADATA

    def __init__(self, meta_file:str=None, meta_dict:dict=None):
        if meta_file: self.file = meta_file
        if meta_dict: self.metadata = meta_dict

    def load_from_meta_file(self):
        pass
    def get_metadata(self):
        return self.metadata if not None else DEFAULT_METADATA
    @staticmethod
    def default_metadata():
        return DEFAULT_METADATA