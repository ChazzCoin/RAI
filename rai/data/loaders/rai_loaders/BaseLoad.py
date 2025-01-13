from langchain_core.document_loaders import BaseLoader
from rai.data.loaders.rai_loaders.BaseDoc import RaiLoaderDocument


class RaiBaseLoader(BaseLoader):
    file_path = ""
    metadata = { 'image':'' }
    data = None
    cache: [RaiLoaderDocument] = None

    def __init__(self, file_path: str, metadata: dict = {'image': ''}):
        self.file_path = file_path
        self.metadata = metadata if not None else { 'image': '' }

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
            print("Failed Loader Validation", e)
            return False