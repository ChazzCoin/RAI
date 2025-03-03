from dataclasses import dataclass, field, fields
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import json
import os
from F.CLASS import Flass
from F.LOG import Log

from rai.assistant.connectors import rAI
from rai.ingest.DataAgent import RaiBaseTextAgent
from rai.ingest.loaders.rai_loaders.BaseLoad import IngestLoaderDocument

Log = Log("RaiMetadataLoader")

DEFAULT_METADATA = {
    'image':''
}

@dataclass
class DataLoaderMetadata(Flass):
    """
    A robust metadata model for data loaders.
    """
    id: str = ''
    title: str = ''
    category: str = ''
    sub_category: Optional[str] = None
    version: Optional[str] = None
    file_type: Optional[str] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the metadata to a dictionary.
        """
        data = self.__dict__.copy()
        # Convert datetime objects to ISO format strings
        data['date_created'] = self.date_created.isoformat() if self.date_created else None
        data['date_modified'] = self.date_modified.isoformat() if self.date_modified else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Get a list of valid field names for the class
        valid_fields = {f.name for f in fields(cls)}
        # Filter out any keys that are not valid field names
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        # Parse ISO format strings back to datetime objects
        if 'date_created' in filtered_data and filtered_data['date_created']:
            filtered_data['date_created'] = datetime.fromisoformat(filtered_data['date_created'])
        else: filtered_data['date_created'] = datetime.now()
        if 'date_modified' in filtered_data and filtered_data['date_modified']:
            filtered_data['date_modified'] = datetime.fromisoformat(filtered_data['date_modified'])
        else: filtered_data['date_modified'] = datetime.now()
        return cls(**filtered_data)

    @classmethod
    def from_json(cls, file_path: str):
        """
        Load metadata from a JSON file.
        """
        if not os.path.exists(file_path):
            Log.e(f"Metadata file not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_json(self, file_path: str):
        """
        Save metadata to a JSON file.
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)


class RaiMetadataLoader:
    ai = rAI()
    meta_ai = False
    meta_file = None
    meta_dict = None
    metadata: DataLoaderMetadata = None
    """
    A robust and production-ready metadata loader for data loaders.
    """
    def __init__(self, meta_file: Optional[str] = None, meta_dict: Optional[Dict[str, Any]] = None, meta_ai:bool= False):
        """
        Initialize the RaiMetadataLoader with a metadata file path or a metadata dictionary.
        Args:
            meta_file (str, optional): Path to the metadata JSON file.
            meta_dict (dict, optional): Dictionary containing metadata.
            meta_ai (bool): Generate Metadata from AI
        """
        self.file: Optional[str] = None
        self.metadata: DataLoaderMetadata = DataLoaderMetadata()
        self.meta_ai = meta_ai
        if meta_file:
            self.meta_file = meta_file
            self.file = meta_file
            self.load_from_meta_file()
        elif meta_dict:
            Log.i("Loading Metadata from dict{}.")
            self.meta_dict = meta_dict
            self.metadata = DataLoaderMetadata.from_dict(meta_dict)
        else: self.metadata = self.default_metadata()

    def load_from_meta_file(self):
        Log.i("Loading Metadata from JSON file.")
        if not self.file: Log.e("Metadata file path is not set.")
        if not os.path.exists(self.file): Log.e(f"Metadata file not found: {self.file}")
        self.metadata = DataLoaderMetadata.from_json(self.file)

    def load_from_meta_dict(self, meta_dict: Dict[str, Any]):
        Log.i("Loading Metadata from dict{}.")
        self.metadata = DataLoaderMetadata.from_dict(meta_dict)

    def has_metadata(self)-> bool:
        if self.metadata: return True
        else: return False
    def get_metadata(self) -> DataLoaderMetadata: return self.metadata

    @staticmethod
    def default_metadata() -> DataLoaderMetadata:
        Log.i("Loading Default Metadata.")
        return DataLoaderMetadata()

    def ai_genny(self, raiDocs: [IngestLoaderDocument]=None, text:str=None):
        try:
            if raiDocs:
                if len(raiDocs) <= 50:
                    data_subset = raiDocs
                else:
                    data_subset = raiDocs[:50]
                temp = ""
                for item in data_subset:
                    temp = f"{temp}\n{item.page_content}"
            elif text:
                temp = text
            else:
                return self.default_metadata()
            meta_result = RaiBaseTextAgent.tool(name="metadata", user_prompt=temp)
            if meta_result:
                meta_dict = json.loads(meta_result)
                final_meta = {}
                for key, value in meta_dict.items():
                    final_meta[str(key)] = str(value)
                return final_meta
            return self.default_metadata()
        except Exception as e:
            print(e)
            return self.default_metadata()
