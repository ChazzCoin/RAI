from files.FilePath import FilePath
from files.read import read_file

""" Use this to open ANY FILE TYPE and return its contents as a str """
def open_file(file: FilePath) -> str:
    return read_file(file)