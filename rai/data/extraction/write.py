import json
import os


def write_to_jsonl(json_object:dict, file_path:str):
    """
    Writes a single JSON object to a .jsonl file.
    - If the file does not exist, creates it and writes the object.
    - If the file exists, appends the object on a new line.

    Args:
        file_path (str): Path to the .jsonl file.
        json_object (dict): JSON object to write to the file.
    """
    try:
        mode = 'a' if os.path.exists(file_path) else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(json.dumps(json_object) + '\n')
    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage
if __name__ == "__main__":
    json_obj = {"name": "John Doe", "age": 30, "city": "New York"}
    file_name = "data.jsonl"
    write_to_jsonl(file_name, json_obj)
