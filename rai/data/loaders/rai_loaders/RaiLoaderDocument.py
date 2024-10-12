

from F.LOG import Log
Log = Log("RaiLoaderDocument")


class RaiLoaderDocument:
    page_content:str
    metadata:dict

    def __init__(self, page_content: str, metadata:dict={ 'image':'' }) -> None:
        self.page_content = page_content
        self.metadata = metadata if not None else { 'image': '' }

