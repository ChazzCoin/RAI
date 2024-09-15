import os
from files.FileImporter import convert_files_to_txt
from files.FilePaths import FilePaths
from assistant.rag import RAGWithChroma
from files.read import read_file
from F import OS

def find_files_with_extension(folder_path, file_ext):
    matching_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(file_ext):
                matching_files.append(os.path.join(root, file))

    return matching_files


def extract_file_names(file_paths):
    file_names = [os.path.basename(path) for path in file_paths]
    return file_names

class ImportProcessor:

    @staticmethod
    def process_raw_files():
        convert_files_to_txt(FilePaths.RAW, FilePaths.PENDING)
        for file in FilePaths(FilePaths.RAW).loop_files():
            if OS.is_directory(file):
                continue
            file_name = FilePaths.get_file_name(file)
            OS.move_file(file, FilePaths.join_to_directory(FilePaths.IMPORTED, file_name))

    @staticmethod
    def process_pending_files(collection_name:str, topic:str):
        rag = RAGWithChroma(collection_name=collection_name)
        for file in FilePaths(FilePaths.PENDING).loop_files():
            contents = read_file(file)
            rag.add_raw_text(raw_text=contents, title=file, topic=topic, url=collection_name)
            OS.move_file(file, os.path.join(FilePaths.PROCESSED, FilePaths.get_file_name(file)))


if __name__ == '__main__':
    ImportProcessor.process_raw_files()