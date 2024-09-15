from F.LOG import Log
from files.FilePath import FilePath
from dataset.TextCleaner import TextCleaner
Log = Log("DataCleaner")

class DataCleaner:

    @staticmethod
    def clean_txt_file():
        for file_contents in FilePath(FilePath.PENDING).add("barrowneuro").loop_files_and_open():
            print(file_contents)
            TextCleaner.clean_text(file_contents)

if __name__ == '__main__':
    DataCleaner.clean_txt_file()