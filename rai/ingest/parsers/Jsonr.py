import json
import os


def read_jsonl_file(file_path):
    """
    Reads a JSONL (JSON Lines) file and returns its contents as a list of dictionaries.

    :param file_path: Path to the JSONL file.
    :return: A list of dictionaries, each representing a JSON object from the file.
    :raises: FileNotFoundError if the file does not exist.
             ValueError if any line in the file is not a valid JSON.
             IOError for any IO related issues.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    json_obj = json.loads(line.strip())
                    data.append(json_obj)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in line: '{line.strip()}'. Error: {str(e)}")
        return data
    except IOError as e:
        raise IOError(f"Error reading file: {file_path}. Error: {str(e)}")

def read_json_file(file_path):
    """
    Reads a JSON file and returns its contents as a Python dictionary.

    :param file_path: Path to the JSON file.
    :return: A dictionary containing the JSON data.
    :raises: FileNotFoundError if the file does not exist.
             ValueError if the file is not a valid JSON.
             IOError for any IO related issues.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {file_path}. Error: {str(e)}")
    except IOError as e:
        raise IOError(f"Error reading file: {file_path}. Error: {str(e)}")


# f = read_json_file("/Users/chazzromeo/Desktop/RelayFuse_2025_2_18_10_6.json")
# for item in f:
#     print(item["file_no"])

import json
import csv




# Read the JSON file
f = read_json_file("/Users/chazzromeo/Desktop/RelayFuse_2025_2_18_10_6.json")

# Define the output CSV file path
csv_file_path = "/Users/chazzromeo/Desktop/RelayFuse_2025_2_18_10_6_file_numbers.csv"

# Write the "file_no" values into a CSV file
with open(csv_file_path, 'w', encoding='utf-8') as csv_file:
    csv_file.write(",".join(str(item["file_no"]) for item in f))

print(f"File numbers saved to {csv_file_path}")
