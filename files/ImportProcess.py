import os
from files.importers import convert_files_to_txt
from files.FilePath import FilePath
from assistant.rag import RAGWithChroma
from files.read import read_file
from F import OS

class ImportProcessor:

    @staticmethod
    def process_raw_files():
        convert_files_to_txt(FilePath.RAW, FilePath.PENDING)
        for file in FilePath(FilePath.RAW).loop_files():
            if OS.is_directory(file):
                continue
            file_name = FilePath.get_file_name(file)
            OS.move_file(file, FilePath.join_to_directory(FilePath.IMPORTED, file_name))

    @staticmethod
    def process_pending_files(collection_name:str, topic:str):
        rag = RAGWithChroma(collection_name=collection_name)
        for file in FilePath(FilePath.PENDING).loop_files():
            contents = read_file(file)
            rag.add_raw_text(raw_text=contents, title=file, topic=topic, url=collection_name)
            OS.move_file(file, os.path.join(FilePath.PROCESSED, FilePath.get_file_name(file)))


if __name__ == '__main__':
    ImportProcessor.process_raw_files()