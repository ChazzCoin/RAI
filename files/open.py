import os, json, csv

PATH = lambda base, file, ext: f"{base}/{file}.{ext}"

class DataLoader:
    data_directory: str

    def __init__(self, data_directory: str):
        self.data_directory = data_directory

    @staticmethod
    def format_file_name(file_name, extension):
        """
        Ensures the file name is formatted correctly by stripping any path and extension,
        and appending the correct extension.
        """
        # Strip the directory and extension if a full path is provided
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        return f"{base_name}.{extension}"

    def PATH(self, default_path, file_name, extension):
        """
        Construct the full file path with the given file name and extension.
        """
        # Format the file name and ensure it has the correct extension
        formatted_file_name = DataLoader.format_file_name(file_name, extension)
        return os.path.join(default_path, formatted_file_name)

    def load_json(self, file_name):
        """
        Load and return the contents of a JSON file.
        """
        try:
            file_path = PATH(self.data_directory, file_name, "json")
            with open(file_path, 'r', encoding='utf-8') as json_file:
                return json.load(json_file)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return None

    def load_jsonl(self, file_name):
        """
        Load and return the contents of a JSONL (JSON Lines) file as a list of dictionaries.
        """
        try:
            file_path = PATH(self.data_directory, file_name, "jsonl")
            with open(file_path, 'r', encoding='utf-8') as jsonl_file:
                return [json.loads(line.strip()) for line in jsonl_file]
        except Exception as e:
            print(f"Error loading JSONL file: {e}")
            return None

    def load_txt(self, file_name):
        """
        Load and return the contents of a plain text file.
        """
        try:
            file_path = PATH(self.data_directory, file_name, "txt")
            with open(file_path, 'r', encoding='utf-8') as txt_file:
                return txt_file.read()
        except Exception as e:
            print(f"Error loading TXT file: {e}")
            return None

    def csv_to_json(self, csv_file_path, json_file_path):
        data = []

        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                data.append(row)

        with open(json_file_path, mode='w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)

        print(f"CSV data successfully converted to JSON and saved to {json_file_path}")

