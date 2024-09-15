import os
from config import env


class FilePaths(str):
    RAW = env("DATA_FILE_PATH_RAW")
    PENDING = env("DATA_FILE_PATH_PENDING")
    PROCESSED = env("DATA_FILE_PATH_PROCESSED")
    IMPORTED = env("DATA_FILE_PATH_IMPORTED")
    OUTPUT = env("DATA_FILE_PATH_OUTPUT")

    def __new__(cls, path = env("DATA_FILE_PATH_OUTPUT")):
        # Create a new instance of the string
        instance = super(FilePaths, cls).__new__(cls, str(path))
        return instance

    def set_path(self, path):
        """
        Update the current path.
        """
        # Since strings are immutable, we return a new instance with the updated path
        return FilePaths(str(path))

    def __repr__(self):
        return f"FilePaths({super().__repr__()})"

    def loop_files(self):
        for file in os.listdir(self):
            yield os.path.join(self, file)

    @staticmethod
    def loop_directory(directory:str):
        for file in os.listdir(directory):
            yield os.path.join(directory, file)

    @staticmethod
    def get_file_name(file_path, no_extension:bool = False):
        # Get the base name (file name with extension)
        file_name_with_extension = os.path.basename(file_path)
        # Split the file name and extension
        file_name_without_extension, _ = os.path.splitext(file_name_with_extension)
        if no_extension:
            return file_name_without_extension
        return file_name_with_extension

    def join_file_name(self, file_name):
        return os.path.join(self, file_name)

    @staticmethod
    def join_to_directory(directory, file_name):
        return os.path.join(directory, file_name)