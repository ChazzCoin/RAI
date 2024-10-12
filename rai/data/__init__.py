import os
import shutil
from pathlib import Path
from typing import Union, Optional
from F.LOG import Log
Log = Log("RaiPath/Files")
class RaiDirectories:
    @staticmethod
    def output() -> str: return f"{RaiPath.get_directory_path(__file__)}/files/output"
    @staticmethod
    def images() -> str: return f"{RaiPath.get_directory_path(__file__)}/files/images"
    @staticmethod
    def imported() -> str: return f"{RaiPath.get_directory_path(__file__)}/files/imported"
    @staticmethod
    def pending() -> str: return f"{RaiPath.get_directory_path(__file__)}/files/pending"
    @staticmethod
    def processed() -> str: return f"{RaiPath.get_directory_path(__file__)}/files/processed"

class RaiPath(str):

    PENDING = "RaiDirectories.pending()"
    PROCESSED = "RaiDirectories.processed()"
    IMPORTED = "RaiDirectories.imported()"
    OUTPUT = "RaiDirectories.output()"

    ADD_EXT = lambda name, ext: f"{name}.{ext}"
    ADD_TXT_EXT = lambda name: f"{name}.txt"
    ADD_JSONL_EXT = lambda name: f"{name}.jsonl"
    ADD_JSON_EXT = lambda name: f"{name}.json"

    def __init__(self, path: Union[str, Path] ="", ignore_exists:bool = True):
        self.PENDING = RaiDirectories.pending()
        self.PROCESSED = RaiDirectories.processed()
        self.IMPORTED = RaiDirectories.imported()
        self.OUTPUT = RaiDirectories.output()
        self.path = Path(path if path != "" else self.PENDING)
        if not self.path.exists() and not ignore_exists:
            raise FileNotFoundError(f"The path '{self.path}' does not exist.")

    def __new__(cls, path: Union[str, Path]=""):
        return super(RaiPath, cls).__new__(cls, path)

    @staticmethod
    def find_directory_path(directory_name: str, start_path: str = "/") -> Optional[str]:
        Log.i(f"RaiPath Search: Finding {directory_name}...")
        for root, dirs, files in os.walk(start_path):
            if directory_name in dirs:
                Log.s("RaiPath Search: Folder found!")
                return os.path.abspath(os.path.join(root, directory_name))
        Log.w("RaiPath Search: Folder not found...")
        return None  # Return None if the directory is not found

    @property
    def is_file(self) -> bool:
        """Check if the entity is a file."""
        return self.path.is_file()

    @property
    def is_directory(self) -> bool:
        """Check if the entity is a directory."""
        return self.path.is_dir()

    def create_file(self, content: str = ""):
        """Create a file with optional content."""
        if self.path.exists():
            raise FileExistsError(f"The file '{self.path}' already exists.")
        if not self.path.parent.exists():
            raise FileNotFoundError(f"The parent directory '{self.path.parent}' does not exist.")
        with open(self.path, 'w') as file:
            file.write(content)

    def read_file(self) -> str:
        """Read and return the content of the file."""
        if not self.is_file:
            raise TypeError(f"'{self.path}' is not a file.")
        with open(self.path, 'r') as file:
            return file.read()

    def create_directory(self, parents: bool = False):
        """Create a directory."""
        if self.path.exists():
            raise FileExistsError(f"The directory '{self.path}' already exists.")
        self.path.mkdir(parents=parents)

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
            raise FileNotFoundError(f"'{self.path}' does not exist.")

    def list_directory(self, files_only: bool = False):
        """List contents of the directory."""
        if not self.is_directory:
            raise TypeError(f"'{self.path}' is not a directory.")
        filtered = []
        for item in list(self.path.iterdir()):
            if item.is_file() and files_only:
                filtered.append(item)
                continue
            if str(item.name).startswith('.'):
                continue
            if item.is_dir() and files_only:
                continue
            filtered.append(item)
        return filtered

    def copy(self, destination: Union[str, Path]):
        """Copy the file or directory to the destination."""
        destination_path = Path(destination)
        if self.is_file:
            shutil.copy2(self.path, destination_path)
        elif self.is_directory:
            if destination_path.exists() and not destination_path.is_dir():
                raise FileExistsError(f"Cannot copy directory '{self.path}' to file '{destination_path}'.")
            shutil.copytree(self.path, destination_path / self.path.name)
        else:
            raise FileNotFoundError(f"'{self.path}' does not exist.")

    def move(self, destination: Union[str, Path]):
        """Move the file or directory to the destination."""
        destination_path = Path(destination)
        shutil.move(str(self.path), str(destination_path))
        self.path = destination_path

    @property
    def size(self) -> int:
        """Get the size of the file or directory in bytes."""
        if self.is_file:
            return self.path.stat().st_size
        elif self.is_directory:
            return sum(f.stat().st_size for f in self.path.rglob('*') if f.is_file())
        else:
            raise FileNotFoundError(f"'{self.path}' does not exist.")

    @property
    def file(self):
        """Yield the file path if it is a file, or yield all files if it is a directory."""
        if self.is_file:
            yield self.path
        elif self.is_directory:
            for file in self.path.rglob('*'):
                if file.is_file():
                    yield file
        else:
            raise FileNotFoundError(f"'{self.path}' does not exist.")

    @property
    def home_directory(self) -> str:
        """Get the path to the current user's home directory."""
        return str(Path.home())

    @property
    def file_name(self) -> str:
        """Get the name of the file."""
        return self.path.name

    @property
    def ext_type(self):
        return self.path.name.split(".")[-1].lower()

    def change_ext_type(self, ext_type:str):
        temp = self.path.name.split(".")[-1].lower()
        new_name = self.path.name.replace(temp, ext_type)
        self.path = self.path.rename(new_name).absolute()
        return self.path

    @property
    def directory_name(self) -> str:
        """Get the name of the directory."""
        if self.is_directory:
            return self.path.name
        else:
            return self.path.parent.name

    @property
    def directory_path(self) -> str:
        return os.path.dirname(self)

    @staticmethod
    def get_directory_path(file_path: str) -> str:
        return os.path.dirname(file_path)

    @staticmethod
    def join_path(path:str, file:str) -> str:
        return str(os.path.join(path, file))

    def yield_files(self):
        """Yield every file in the directory."""
        if self.is_directory:
            for file in self.path.rglob('*'):
                if file.is_file():
                    yield file
        else:
            print("No files found.")

    def is_metadata_file(self):
        if self.is_file:
            if self.endswith("metadata.json"):
                return True
        return False

    def __str__(self) -> str:
        return self.path.absolute().__str__()

    def __repr__(self) -> str:
        return self.__str__()

# Example Usage
if __name__ == "__main__":
    # Initialize a file or directory
    entity = RaiPath(__file__)
    print(entity.directory_path)
    # Example operations
    # if entity.is_file:
    #     print("File Size:", entity.size, "bytes")
    # elif entity.is_directory:
    #     print("Directory Contents:", entity.list_directory())