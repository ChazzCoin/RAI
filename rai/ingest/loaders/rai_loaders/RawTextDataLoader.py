from F.LOG import Log

from rai.raigents.base.BaseLoaders import register_loader
from rai.ingest.loaders.rai_loaders.BaseLoad import RaiBaseLoader, RaiLoaderDocument

Log = Log("RawTextDataLoader")

@register_loader(name="text")
class RawTextDataLoader(RaiBaseLoader):
    cache: [RaiLoaderDocument] = None
    def __init__(self, raw_text: str, file_path: str, metadata={'image': ''}):
        super().__init__(file_path, metadata)
        self.data = raw_text
        self.metadata = metadata if not None else { 'image': '' }

    def load(self):
        if self.cache:
            Log.i(f"Returning Cached Loader: [ Raw Text ]")
            return self.cache
        self.cache = [RaiLoaderDocument(page_content=self.data, metadata=self.metadata)]
        return self.cache