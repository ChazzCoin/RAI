import os
import time

from F.LOG import Log

from rai.data.extraction.intake.Vision import VisionExtractor
from rai.data.loaders import delete_folder
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument, RaiBaseLoader

Log = Log("VisionDataLoader")

class VisionDataLoader(RaiBaseLoader):

    def __init__(self, file_path: str, metadata: dict = {'image': ''}):
        super().__init__(file_path, metadata)
        self.data = VisionExtractor(self.file_path).extract(save_images=True)

    def load(self, load_text=True, load_images=True):
        Log.w("VisionDataLoader [ load() ] has been called.")
        if not load_text and not load_images:
            return []
        if self.cache:
            Log.i(f"Returning Cached Loader: [ {self.file_path} ]")
            return self.cache
        for page in self.data:
            content = ""
            if load_text:
                content = page.get('page_content', '')
            if load_images:
                self.metadata['image'] = page.get('image', '')
            self.cache.append(RaiLoaderDocument(page_content=content, metadata=self.metadata))
        return self.cache

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

    def load_d(self):
        if self.data is None:
            self.load()
        documents = []
        for page in self.data:
            page_content = page.get('page_content', '')
            metadata = {'image': page.get('image', '')}
            documents.append(RaiLoaderDocument(page_content=page_content, metadata=metadata))
        return documents

    @staticmethod
    def validate_vision_results(page_texts: list):
        """
        Validates that the page_texts list contains valid data.

        The list should:
        - Not be None
        - Not be empty
        - Contain no empty objects within it
        - Contain objects that match the structure {'page_content': '', 'image_path': ''}

        Args:
            page_texts (list): The list to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if page_texts is None:
            return False
        if not isinstance(page_texts, list):
            return False
        if len(page_texts) == 0:
            return False
        for index, item in enumerate(page_texts):
            if not isinstance(item, dict):
                return False
            if len(item) == 0:
                return False
            expected_keys = {'page_content', 'image_path'}
            if set(item.keys()) != expected_keys:
                return False
            if not isinstance(item['page_content'], str):
                return False
            if not isinstance(item['image_path'], str):
                return False
        return True
