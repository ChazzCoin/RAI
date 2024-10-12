import os
import time

from F.LOG import Log

from rai.data.extraction.intake.Vision import VisionExtractor
from rai.data.loaders import delete_folder
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiLoaderDocument

Log = Log("VisionDataLoader")

class VisionDataLoader:

    def __init__(self, file_path: str, metadata:dict={ 'image': '' }, delete_cache=True):
        self.file_path = file_path
        self.metadata = metadata if not None else {'image': ''}
        self.data = VisionExtractor(self.file_path).extract(save_images=True)
        if delete_cache:
            # self.delete_cached_folder()
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
            if load_text:
                content = page.get('page_content', '')
            if load_images:
                self.metadata['image'] = page.get('image', '')
            filtered_data.append(RaiLoaderDocument(page_content=content, metadata=self.metadata))
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
        if not self.data:
            return True
        return False

    def should_fallback(self):
        if not self.data:
            Log.w("No Vision Data. Falling Back.")
            return True
        Log.w("Vision Found Data.")
        return False

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
