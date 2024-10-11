
import shutil
from pathlib import Path
from typing import Union

class RaiPath:

    RAW = "DATA_FILE_PATH_RAW"
    PENDING = "DATA_FILE_PATH_PENDING"
    PROCESSED = "DATA_FILE_PATH_PROCESSED"
    IMPORTED = "DATA_FILE_PATH_IMPORTED"
    OUTPUT = "DATA_FILE_PATH_OUTPUT"

    def __init__(self, path: Union[str, Path] = None):
        self.path = Path(path or self.RAW)
        if not self.path.exists():
            raise FileNotFoundError(f"The path '{self.path}' does not exist.")

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

    def yield_files(self):
        """Yield every file in the directory."""
        if self.is_directory:
            for file in self.path.rglob('*'):
                if file.is_file():
                    yield file
        else:
            print("No files found.")

    def __str__(self) -> str:
        return f"FileSystemEntity(path='{self.path}')"

    def __repr__(self) -> str:
        return self.__str__()

# Example Usage
if __name__ == "__main__":
    # Initialize a file or directory
    entity = RaiPath("/Users/chazzromeo/Desktop/data/PCSC Player Handbook.pdf")

    # Example operations
    if entity.is_file:
        print("File Size:", entity.size, "bytes")
    elif entity.is_directory:
        print("Directory Contents:", entity.list_directory())