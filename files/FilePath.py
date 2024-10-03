from config import env
# from files.read import read_file
from F import OS
import os

class FilePath:
    RAW = env("DATA_FILE_PATH_RAW")
    PENDING = env("DATA_FILE_PATH_PENDING")
    PROCESSED = env("DATA_FILE_PATH_PROCESSED")
    IMPORTED = env("DATA_FILE_PATH_IMPORTED")
    OUTPUT = env("DATA_FILE_PATH_OUTPUT")

    def __init__(self, path=None):
        self._path = path or env("DATA_FILE_PATH_OUTPUT")

    def set_path(self, path):
        self._path = path

    def path(self):
        return self._path

    def __repr__(self):
        return f"FilePath({self._path})"

    def __str__(self):
        return self._path

    def loop_files(self):
        for file in os.listdir(self._path):
            yield os.path.join(self._path, file)

    # def loop_files_and_open(self):
    #     for file in os.listdir(self._path):
    #         yield read_file(FilePath(os.path.join(self._path, file)).path())

    @staticmethod
    def loop_directory(directory: str):
        for file in os.listdir(directory):
            yield os.path.join(directory, file)

    @staticmethod
    def loop_directory_and_open(directory: str):
        for file in os.listdir(directory):
            yield read_file(FilePath(os.path.join(directory, file)).path())

    @staticmethod
    def get_file_name(file_path, no_extension: bool = False):
        file_name_with_extension = os.path.basename(file_path)
        file_name_without_extension, _ = os.path.splitext(file_name_with_extension)
        return file_name_without_extension if no_extension else file_name_with_extension

    def get_name_of_file(self, no_extension: bool = False):
        if self.is_directory():
            return self._path
        file_name_with_extension = os.path.basename(self._path)
        file_name_without_extension, _ = os.path.splitext(file_name_with_extension)
        return file_name_without_extension if no_extension else file_name_with_extension

    def add(self, *paths:str):
        for p in paths:
            self._path = os.path.join(self._path, str(p))
        return self

    def temp_add(self, *paths:str):
        temp = self._path
        for p in paths:
            temp = os.path.join(temp, str(p))
        return temp

    def join_file_name(self, file_name):
        self._path = os.path.join(self._path, file_name)
        return self

    def open(self):
        return read_file(self._path)

    @staticmethod
    def join_to_directory(directory, file_name):
        return os.path.join(directory, file_name)

    def is_directory(self):
        return os.path.isdir(self._path)

    def is_file(self):
        return os.path.isfile(self._path)

    def is_media_file(self):
        # Placeholder for media file check logic
        return OS.is_media_file(self._path)

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



# class FilePath(str):
#     RAW = env("DATA_FILE_PATH_RAW")
#     PENDING = env("DATA_FILE_PATH_PENDING")
#     PROCESSED = env("DATA_FILE_PATH_PROCESSED")
#     IMPORTED = env("DATA_FILE_PATH_IMPORTED")
#     OUTPUT = env("DATA_FILE_PATH_OUTPUT")
#
#     def __new__(cls, path = env("DATA_FILE_PATH_OUTPUT")):
#         # Create a new instance of the string
#         instance = super(FilePath, cls).__new__(cls, str(path))
#         return instance
#
#     def set_path(self, path):
#         """
#         Update the current path.
#         """
#         # Since strings are immutable, we return a new instance with the updated path
#         return FilePath(str(path))
#
#     def __repr__(self):
#         return f"FilePaths({super().__repr__()})"
#
#     def loop_files(self):
#         for file in os.listdir(self):
#             yield os.path.join(self, file)
#
#     @staticmethod
#     def loop_directory(directory:str):
#         for file in os.listdir(directory):
#             yield os.path.join(directory, file)
#
#     @staticmethod
#     def get_file_name(file_path, no_extension:bool = False):
#         # Get the base name (file name with extension)
#         file_name_with_extension = os.path.basename(file_path)
#         # Split the file name and extension
#         file_name_without_extension, _ = os.path.splitext(file_name_with_extension)
#         if no_extension:
#             return file_name_without_extension
#         return file_name_with_extension
#
#     def get_name_of_file(self, no_extension:bool = False):
#         if self.is_directory():
#             return self
#         # Get the base name (file name with extension)
#         file_name_with_extension = os.path.basename(self)
#         # Split the file name and extension
#         file_name_without_extension, _ = os.path.splitext(file_name_with_extension)
#         if no_extension:
#             return file_name_without_extension
#         return file_name_with_extension
#
#     def add_path(self, path):
#         return os.path.join(self, path)
#
#     def join_file_name(self, file_name):
#         return os.path.join(self, file_name)
#
#     @staticmethod
#     def join_to_directory(directory, file_name):
#         return os.path.join(directory, file_name)
#
#     def is_directory(self):
#         return OS.is_directory(self)
#
#     def is_file(self):
#         return OS.is_file(self)
#
#     def is_media_file(self):
#         return OS.is_media_file(self)