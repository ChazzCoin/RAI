import json, os
from files.FilePaths import FilePaths

PATH = lambda base, file, ext: f"{base}/{file}.{ext}"

class DataSaver:

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
    def save_json(data, file_name, output:FilePaths):
        """
        Save data as a JSON file.
        """
        try:
            file_path = DataSaver.PATH(output, file_name, "json")
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4)
            print(f"Data successfully saved to {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

    @staticmethod
    def save_jsonl(data, file_name, output:FilePaths):
        """
        Save data as a JSONL (JSON Lines) file.
        Each item in the data should be written on a new line as a valid JSON object.
        """
        try:
            file_path = DataSaver.PATH(output, file_name, "jsonl")
            with open(file_path, 'w', encoding='utf-8') as jsonl_file:
                for item in data:
                    jsonl_file.write(json.dumps(item) + '\n')
            print(f"Data successfully saved to {file_path}")
        except Exception as e:
            print(f"Error saving JSONL file: {e}")

    @staticmethod
    def save_txt(data, output:FilePaths):
        """
        Save data as a plain text file.
        """
        try:
            with open(output, 'w', encoding='utf-8') as txt_file:
                if isinstance(data, list):
                    txt_file.write("\n".join(data))
                else:
                    txt_file.write(data)
            print(f"Data successfully saved to {output}")
        except Exception as e:
            print(f"Error saving TXT file: {e}")


if __name__ == '__main__':
    # Example usage:

    # Save JSON
    data = {"name": "John", "age": 30, "hobbies": ["reading", "swimming"]}
    DataSaver.save_json(data, "output.json", FilePaths())

    # Save JSONL
    data_list = [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30},
        {"name": "Charlie", "age": 35}
    ]
    DataSaver.save_jsonl(data_list, "output.jsonl")

    # Save plain text
    text_data = "This is some text data to be saved in a file."
    DataSaver.save_txt(text_data, "output.txt")

    # Save list of text lines as plain text
    lines_data = ["First line", "Second line", "Third line"]
    DataSaver.save_txt(lines_data, "output_lines.txt")
