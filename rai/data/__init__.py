import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Union, Optional
from F.LOG import Log
from F import OS
Log = Log("RaiPath/Files")

class RaiDirectories:
    @staticmethod
    def output() -> str: return f"{OS.get_path(__file__)}/files/output"
    @staticmethod
    def images() -> str: return f"{OS.get_path(__file__)}/files/images"
    @staticmethod
    def imported() -> str: return f"{OS.get_path(__file__)}/files/imported"
    @staticmethod
    def pending() -> str: return f"{OS.get_path(__file__)}/files/pending"
    @staticmethod
    def processed() -> str: return f"{OS.get_path(__file__)}/files/processed"

class RaiPath(str):

    OUTPUT = RaiDirectories.output

    ADD_EXT = lambda name, ext: f"{name}.{ext}"
    ADD_TXT_EXT = lambda name: f"{name}.txt"
    ADD_JSONL_EXT = lambda name: f"{name}.jsonl"
    ADD_JSON_EXT = lambda name: f"{name}.json"

    def __new__(cls, *args, **kwargs):
        if args: path = args[0]
        else: path = kwargs.get('path', "")
        return super(RaiPath, cls).__new__(cls, path)

    def __init__(self, path: Union[str, Path] ="", directory_name:str=None, file_name:str=None, ignore_exists:bool = True):
        self.PENDING = RaiDirectories.pending()
        self.PROCESSED = RaiDirectories.processed()
        self.IMPORTED = RaiDirectories.imported()
        self.OUTPUT = RaiDirectories.output()
        self.path = self.parse(path if path != "" else __path__)
        if directory_name is not None:
            self.path = self.parse(self.find_directory(directory_name))
        if file_name is not None:
            self.path = self.parse(self.find_file(file_name))
        if not self.path.exists() and not ignore_exists:
            if self.create_directory(path):
                Log.w(f"No path found, auto generated the directory: [ {path} ]")
            Log.e(f"The path '{self.path}' does not exist and could not be created.")

    # def __new__(cls, path: Union[str, Path]=""):
    #     return super(RaiPath, cls).__new__(cls, path)


    @staticmethod
    def find_directory(directory_name: str, start_path: str = "/") -> Optional[str]:
        Log.i(f"Searching for Directory: [ {directory_name} ]")
        for root, dirs, files in os.walk(start_path):
            if directory_name in dirs:
                Log.s("RaiPath Search: Folder found!")
                return os.path.abspath(os.path.join(root, directory_name))
        Log.w("RaiPath Search: Folder not found...")
        return None

    @staticmethod
    def find_file(file_name: str, start_path: str = "/") -> Optional[str]:
        Log.i(f"Searching for File: [ {file_name} ]")
        for root, dirs, files in os.walk(start_path):
            if file_name in files:
                Log.s("RaiPath Search: Folder found!")
                return os.path.abspath(os.path.join(root, file_name))
        Log.w("RaiPath Search: Folder not found...")
        return None

    def exists(self) -> bool:
        return self.path.exists()

    def create_file(self, content: str = ""):
        """Create a file with optional content."""
        if self.path.exists():
            Log.e(f"The file '{self.path}' already exists.")
        if not self.path.parent.exists():
            Log.e(f"The parent directory '{self.path.parent}' does not exist.")
        with open(self.path, 'w') as file:
            file.write(content)

    def read_file(self) -> str:
        if not self.is_file: Log.e(f"'{self.path}' is not a file.")
        with open(self.path, 'r') as file: return file.read()

    def delete(self, recursive: bool = False):
        """Delete the file or directory."""
        if self.is_file:
            self.path.unlink()
        elif self.is_directory:
            if recursive:
                shutil.rmtree(self.path)
            else:
                self.path.rmdir()
        else:
            Log.e(f"'{self.path}' does not exist.")

    def list_directory(self, files_only: bool = False):
        """List contents of the directory."""
        if not self.is_directory:
            Log.e(f"'{self.path}' is not a directory.")
        filtered = []
        for item in list(self.path.iterdir()):
            if item.is_file() and files_only:
                filtered.append(item)
                continue
            if str(item.name).startswith('.'): continue
            if item.is_dir() and files_only: continue
            filtered.append(item)
        return filtered

    def copy(self, destination: Union[str, Path]):
        """Copy the file or directory to the destination."""
        destination_path = Path(destination)
        if self.is_file: shutil.copy2(self.path, destination_path)
        elif self.is_directory:
            if destination_path.exists() and not destination_path.is_dir():
                Log.e(f"Cannot copy directory '{self.path}' to file '{destination_path}'.")
            shutil.copytree(self.path, destination_path / self.path.name)
        else: Log.e(f"'{self.path}' does not exist.")

    def move(self, destination: Union[str, Path]):
        """Move the file or directory to the destination."""
        destination_path = Path(destination)
        shutil.move(str(self.path), str(destination_path))
        self.path = destination_path

    @property
    def size(self) -> int:
        """Get the size of the file or directory in bytes."""
        if self.is_file: return self.path.stat().st_size
        elif self.is_directory: return sum(f.stat().st_size for f in self.path.rglob('*') if f.is_file())
        else: Log.e(f"'{self.path}' does not exist.")

    @property
    def file(self):
        if self.is_file: yield self.path
        elif self.is_directory:
            for file in self.path.rglob('*'):
                if file.is_file(): yield file
        else: Log.e(f"'{self.path}' does not exist.")

    @staticmethod
    def has_extension(file_path: str) -> bool:
        _, extension = os.path.splitext(file_path)
        return bool(extension)

    def change_ext_type(self, ext_type:str):
        temp = self.path.name.split(".")[-1].lower()
        new_name = self.path.name.replace(temp, ext_type)
        self.path = self.path.rename(new_name).absolute()
        return self.path

    @property
    def directory_name(self) -> str:
        """Get the name of the directory."""
        if self.is_directory: return self.path.name
        else: return self.path.parent.name

    @staticmethod
    def parse(path): return Path(path)
    @property
    def is_file(self) -> bool: return self.path.is_file()
    @property
    def is_directory(self) -> bool: return self.path.is_dir()
    @property
    def home_directory(self) -> str: return str(Path.home())
    @property
    def file_name(self) -> str: return self.path.name
    @property
    def ext_type(self): return self.path.name.split(".")[-1].lower()
    @property
    def directory_path(self) -> str: return os.path.dirname(self)
    @staticmethod
    def get_directory_path(file_path: str) -> str: return os.path.dirname(file_path)
    @staticmethod
    def join_path(path:str, file:str) -> str: return str(os.path.join(path, file))

    def yield_files(self):
        """Yield every file in the directory."""
        if self.is_directory:
            for file in self.path.rglob('*'):
                if file.is_file(): yield file
        else: Log.e("No files found.")

    def is_metadata_file(self):
        if self.is_file:
            if self.endswith("metadata.json"): return True
        return False

    def verify_create_directory(self):
        if not self.path.exists(): self.create_directory(self)

    @staticmethod
    def create_directory(path: str) -> bool:
        try:
            # Attempt to create the directory
            os.makedirs(path, exist_ok=True)
            # Check if the path is indeed a directory
            if not os.path.isdir(path):
                Log.e(f"A non-directory file with the same name as '{path}' already exists.")
                return False
            Log.i(f"Directory '{path}' is ready.")
            return True
        except PermissionError as e: Log.e(f"Permission denied: Cannot create directory '{path}'. {e}")
        except FileExistsError as e: Log.e(f"File exists and is not a directory: '{path}'. {e}")
        except OSError as e: Log.e(f"OS error occurred while creating directory '{path}': {e}")
        return False

    @staticmethod
    def sanitize_file_name_for_chromadb(file_name: str, max_length: int = 64) -> str:
        filename = RaiPath(file_name)
        # Normalize the Unicode string to decompose combined characters
        file_name = unicodedata.normalize('NFKD', file_name)
        # Remove accents and diacritics
        file_name = file_name.encode('ascii', 'ignore').decode('ascii')
        # Convert to lowercase
        file_name = file_name.lower()
        # Replace any sequence of invalid characters with a single underscore
        # Allowed characters: alphanumeric, underscore, hyphen
        file_name = re.sub(r'[^a-z0-9_\-]+', '_', file_name)
        # Remove leading and trailing underscores or hyphens
        file_name = file_name.strip('_-')
        # Truncate to the maximum allowed length
        file_name = file_name[:max_length]
        file_name = file_name.replace(".", "_")
        file_name = file_name.replace("-", "_")
        # Ensure the name is not empty after sanitization
        if not file_name:
            return filename

        return file_name
    def __str__(self) -> str: return self.path.absolute().__str__()
    def __repr__(self) -> str: return self.__str__()

# Example Usage
if __name__ == "__main__":
    # Initialize a file or directory
    # entity = RaiPath(__file__)
    sanny = RaiPath.sanitize_file_name_for_chromadb("all-team-assignment-players.csv")
    print(sanny)
    # Example operations
    # if entity.is_file:
    #     print("File Size:", entity.size, "bytes")
    # elif entity.is_directory:
    #     print("Directory Contents:", entity.list_directory())