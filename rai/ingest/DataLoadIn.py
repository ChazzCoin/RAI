import json
import os

from F import LIST, DATE
from rai.ingest.utilities.TextUtils import TextProcessor, FormatProcessor
from rai.ingest.files.write import write_to_jsonl, write_to_json
from rai.internal.connectors import VECTOR_DB_CLIENT



"""
**FORMAT AND CLEAN DATA**
- Grammar Check.
- Spell Check.
- Remove Unwanted Characters/Bad Characters.
- Remove any text/data that would breach or go against OpenAI Terms of Service

**ENHANCE DATA**
- 
"""

""" Step 1. Get and Format Data Structure """
class DataBaseProcessor(TextProcessor, FormatProcessor):
    output_type = 'json'
    prefix = ""
    output_file = ""
    input_file = ""
    raw_data = []
    prepared_data = []
    to_save_data = []

    def __init__(self, prefix=None, output_file=None, output_type='json', input_file=None):
        self.prefix = prefix
        self.output_file = output_file
        self.output_type = output_type
        self.input_file = input_file
        if input_file: self.load_from_file()
        elif prefix: self.get_set_raw_data(prefix)
        # If we're expecting JSON output and the file doesn't exist yet, create it with an empty array
        if self.output_type == 'json' and self.output_file and not os.path.exists(self.output_file):
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("[]")

    def get_set_raw_data(self, prefix):
        collections = VECTOR_DB_CLIENT.get_all_collections_by_chain(prefix)
        for collection in collections:
            docs = VECTOR_DB_CLIENT.get(collection)
            for doc in docs.documents:
                if type(doc) in [list, tuple]:
                    for item in doc:
                        self.raw_data.append(item)
                elif type(doc) in [str]:
                    self.raw_data.append(doc)
                else:
                    self.raw_data.append(str(doc))
        self.raw_data = LIST.flatten(self.raw_data)
        return self.raw_data

    def get_cleaned_data(self):
        cleaned = []
        for item in self.raw_data:
            cleaned.append(self.TEXT_CLEANER(item))
        return cleaned

    def get_pretrain_data(self):
        for doc in self.raw_data:
            if type(doc) in [list, tuple]:
                for item in doc:
                    self.prepared_data.append(self.TO_PRETRAIN(item))
            elif type(doc) in [str]:
                self.prepared_data.append(self.TO_PRETRAIN(doc))
            else:
                self.prepared_data.append(self.TO_PRETRAIN(doc))
        self.jsonl_writer()
        return self.prepared_data

    def load_from_file(self):
        # If no file path specified, return empty
        if not self.input_file:
            return []
        # If file doesn't exist, return empty
        if not os.path.exists(self.input_file):
            return []

        # Handle JSON
        if self.output_type == 'json':
            try:
                with open(self.input_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.raw_data = LIST.merge_lists(self.raw_data, data)
                return self.raw_data
            except json.JSONDecodeError:
                print(f"Warning: {self.input_file} has invalid JSON.")
                return []
            except Exception as e:
                print(f"Error loading JSON from file {self.input_file}: {e}")
                return []

        # Handle JSONL (each line is a valid JSON object)
        elif self.output_type == 'jsonl':
            items = []
            try:
                with open(self.input_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue  # skip empty lines if any
                        try:
                            item = json.loads(line)
                            items.append(item)
                            self.raw_data.append(item)
                        except json.JSONDecodeError:
                            # You could decide to raise an error or skip malformed lines
                            print(f"Warning: Skipping invalid JSON line: {line}")
                            continue
                return items
            except Exception as e:
                print(f"Error loading JSONL from file {self.input_file}: {e}")
                return []

        # Handle other output types (not implemented)
        else:
            return []
    def jsonl_single_writer(self, item):
        if not self.output_file: return
        write_to_jsonl(item, file_path=self.output_file)
    def jsonl_writer(self):
        if not self.output_file: return
        elif self.output_type == 'jsonl':
            for item in self.to_save_data:
                write_to_jsonl(item, file_path=self.output_file)
    def json_writer(self):
        """
        Saves self.to_save_data to the file as JSON (or another format based on output_type).
        If the file already has data, merge the new data instead of overwriting it.
        """
        if not self.output_file:
            return  # No output file specified, skip

        if self.output_type == 'json':
            # Read existing data from file (if any) and merge
            existing_data = []
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = []

            # Merge existing data with current self.to_save_data
            merged_data = existing_data + self.to_save_data

            # Write merged data back to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)

            # Clear self.to_save_data so we don’t re-append the same items on the next save
            self.to_save_data.clear()

        else:
            # For other output types, implement suitable saving logic
            pass


