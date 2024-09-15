import json, os
from F.LOG import Log
PATH = lambda base, file, ext: f"{base}/{file}.{ext}"
Log = Log("DataSaver")

class DataSaver:

    @staticmethod
    def ensure_directory_exists(directory_path):
        """
        Checks if the specified directory exists, and if it doesn't, creates it.

        :param directory_path: Path to the directory.
        """
        if not os.path.exists(directory_path):
            try:
                os.makedirs(directory_path)
                print(f"Directory created: {directory_path}")
            except Exception as e:
                print(f"Error creating directory: {e}")
        else:
            print(f"Directory already exists: {directory_path}")

    @staticmethod
    def format_file_name(file_name, extension):
        """
        Ensures the file name is formatted correctly by stripping any path and extension,
        and appending the correct extension.
        """
        # Strip the directory and extension if a full path is provided
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        return f"{base_name}.{extension}"

    @staticmethod
    def PATH(default_path, file_name, extension):
        """
        Construct the full file path with the given file name and extension.
        """
        # Format the file name and ensure it has the correct extension
        formatted_file_name = DataSaver.format_file_name(file_name, extension)
        return os.path.join(default_path, formatted_file_name)

    @staticmethod
    def save_json(data, file_name, output:str):
        """
        Save data as a JSON file.
        """
        try:
            file_path = DataSaver.PATH(output, file_name, "json")
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4)
            Log.s(f"Data successfully saved to {file_path}")
        except Exception as e:
            Log.e(f"Error saving JSON file: {e}")

    @staticmethod
    def save_jsonl(data, file_name, output:str):
        """
        Save data as a JSONL (JSON Lines) file.
        Each item in the data should be written on a new line as a valid JSON object.
        """
        try:
            file_path = DataSaver.PATH(output, file_name, "jsonl")
            with open(file_path, 'w', encoding='utf-8') as jsonl_file:
                for item in data:
                    jsonl_file.write(json.dumps(item) + '\n')
            Log.s(f"Data successfully saved to {file_path}")
        except Exception as e:
            Log.e(f"Error saving JSONL file: {e}")

    @staticmethod
    def save_txt(data, output:str):
        """
        Save data as a plain text file.
        """
        try:
            with open(output, 'w', encoding='utf-8') as txt_file:
                if isinstance(data, list):
                    txt_file.write("\n".join(data))
                else:
                    txt_file.write(data)
            Log.s(f"Data successfully saved to {output}")
        except Exception as e:
            Log.e(f"Error saving TXT file: {e}")
