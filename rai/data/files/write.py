import json
import os


def write_to_jsonl(json_object:dict, file_path:str):
    try:
        if not file_path.endswith('.jsonl'):
            file_path += '.jsonl'
        mode = 'a' if os.path.exists(file_path) else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(json.dumps(json_object) + '\n')
    except Exception as e:
        print(f"An error occurred: {e}")

def write_to_json(json_objects: list, file_path: str):
    try:
        if not file_path.endswith('.json'):
            file_path += '.json'
        if os.path.exists(file_path):
            # If the file exists, load existing data and append new objects
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    raise ValueError("Existing file content is not a list")
            json_objects = existing_data + json_objects

        # Write the combined data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_objects, f, indent=4)
    except Exception as e:
        print(f"An error occurred: {e}")

