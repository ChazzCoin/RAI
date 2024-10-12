from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import json
import os
from F.LOG import Log
from rai.assistant.ollama_client import ollama_generate
from rai.assistant.ai import RaiAi
from rai.data.loaders.rai_loaders.RaiLoaderDocument import RaiBaseLoader

Log = Log("RaiMetadataLoader")

DEFAULT_METADATA = {
    'image':''
}

@dataclass
class DataLoaderMetadata:
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
        """
        Create a DataLoaderMetadata instance from a dictionary.
        """
        data = data.copy()
        # Parse ISO format strings back to datetime objects
        if 'date_created' in data and data['date_created']:
            data['date_created'] = datetime.fromisoformat(data['date_created'])
        if 'date_modified' in data and data['date_modified']:
            data['date_modified'] = datetime.fromisoformat(data['date_modified'])
        return cls(**data)

    @classmethod
    def from_json(cls, file_path: str):
        """
        Load metadata from a JSON file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Metadata file not found: {file_path}")
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
    ai = RaiAi()
    metadata: DataLoaderMetadata = None
    """
    A robust and production-ready metadata loader for data loaders.
    """
    def __init__(self, meta_file: Optional[str] = None, meta_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the RaiMetadataLoader with a metadata file path or a metadata dictionary.
        Args:
            meta_file (str, optional): Path to the metadata JSON file.
            meta_dict (dict, optional): Dictionary containing metadata.
        """
        self.file: Optional[str] = None
        self.metadata: DataLoaderMetadata = DataLoaderMetadata()
        if meta_file:
            self.file = meta_file
            self.load_from_meta_file()
        elif meta_dict:
            Log.i("Loading Metadata from dict{}.")
            self.metadata = DataLoaderMetadata.from_dict(meta_dict)
        else:
            self.metadata = self.default_metadata()

    def load_from_meta_file(self):
        """
        Load metadata from the specified JSON file.
        """
        Log.i("Loading Metadata from JSON file.")
        if not self.file:
            raise ValueError("Metadata file path is not set.")
        if not os.path.exists(self.file):
            raise FileNotFoundError(f"Metadata file not found: {self.file}")
        self.metadata = DataLoaderMetadata.from_json(self.file)

    def get_metadata(self) -> DataLoaderMetadata:
        """
        Get the metadata object.
        Returns: DataLoaderMetadata: The metadata object.
        """
        return self.metadata

    @staticmethod
    def default_metadata() -> DataLoaderMetadata:
        """
        Return a default metadata object.
        Returns: DataLoaderMetadata: The default metadata object.
        """
        Log.i("Loading Default Metadata.")
        return DataLoaderMetadata()

    def generate_metadata(self, data_loader: RaiBaseLoader, override_file:bool=False) -> None:
        """
        Analyzes a subset of data from the DataLoader using an AI model and updates the metadata.
        Args:
            data_loader (DataLoader): The data loader instance containing the data.
            subset_indices (List[int]): Indices of the data subset to analyze.
        Returns:
            None
        """
        if not override_file:
            if self.metadata:
                return
        Log.i("Generating Metadata from AI.")
        # Step 1: Extract the subset of data
        data_subset = data_loader.get_subset(50)
        # Step 2: Prepare data for AI analysis
        prepared_data = self.prepare_data_for_ai(data_subset)
        # Step 3: Send data to AI model for analysis
        self.ai_generate_metadata(prepared_data)

    def prepare_data_for_ai(self, data_subset: List[Any]) -> List[str]:
        """
        Prepares the data subset for AI analysis.
        Args:
            data_subset (List[Any]): The subset of data to prepare.
        Returns:
            List[str]: The prepared data suitable for AI analysis.
        """
        prepared_data = []
        for data in data_subset:
            # Assuming data is text; adjust preprocessing as needed
            text = str(data).strip()
            # Additional preprocessing can be added here
            prepared_data.append(text)
        return prepared_data

    def ai_generate_metadata(self, prepared_data: List[str], count:int=0):
        """
        Analyzes the prepared data using an AI model.
        Args:
            prepared_data (List[str]): The data prepared for AI analysis.
        Returns:
            Dict[str, Any]: The AI analysis results.
        """
        response = self.ai.generate(
            engine_name="openai",
            system_prompt=f"""
            !!GOLDEN RESPONSE RULE!!
            ->ONLY RETURN THE JSON METADATA OBJECT. NOTHING ELSE.<-
            """,
            user_prompt=f"""
            You will read the following content and you will extract out the following metadata details.
            1. Look at each key name in the model and then try to determine the value for the key, based on the content.
            2. Extract keywords and some of the most important words used or the topic/category the text is about as tags.
            3. Only look for the model details.
            4. Return the exact metadata model I give you. Do not change anything.
            5. Try to guess the overall context and attempt to fill out all attributes even if you don't know.
            
            METADATA MODEL:
            {self.default_metadata()}
            
            CONTENT:
            {prepared_data}
            
            RESPONSE RULE:
            ONLY RETURN THE JSON METADATA OBJECT.
            """
        )
        metadata_json = response.strip()
        metadata = self.parse_ai_response(metadata_json)
        if not metadata:
            if count < 3:
                self.ai_generate_metadata(prepared_data, count=count + 1)
        if metadata: self.metadata = DataLoaderMetadata.from_dict(metadata)

    def parse_ai_response(self, response_text: str, count:int=0) -> Dict[str, Any]:
        metadata = None
        try:
            metadata = json.loads(response_text)
        except json.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            if count == 2:
                return metadata
            elif count == 0:
                temp = self.extract_json_with_regex(response_text)
                if temp:
                    return self.parse_ai_response(temp, count + 1)
            elif count == 1:
                temp = self.extract_json(response_text)
                if temp:
                    return self.parse_ai_response(temp, count + 1)
        return metadata

    @staticmethod
    def extract_json_with_regex(text):
        import regex
        pattern = r'\{(?:[^{}]|(?0))*\}'
        match = regex.search(pattern, text, regex.DOTALL)
        if match:
            return match.group(0)
        else:
            return None
    @staticmethod
    def extract_json(text):
        start = text.find('{')
        if start == -1:
            return None  # No opening brace found

        stack = []
        for idx in range(start, len(text)):
            char = text[idx]
            if char == '{':
                stack.append('{')
            elif char == '}':
                if not stack:
                    return None  # More closing braces than opening
                stack.pop()
                if not stack:
                    return text[start:idx + 1]
        return None  # No matching closing brace found