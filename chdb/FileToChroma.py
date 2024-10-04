import os
import time
import uuid

from dataset.TextCleaner import TextCleaner
from F import DATE
from chdb.rag import RAGWithChroma
from files.read import read_file
from dataset.intake.Jsonr import read_jsonl_file

""" MASTER """
class FileToChromaConverter(RAGWithChroma):
    character_limit = 1500

    def __create_jsonl_documents(self, collection, id, text, url, title, topic):
        chunks = TextCleaner.split_string_by_limit(text, char_limit=self.character_limit)
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                'id': f"{id}_{uuid.uuid4()}",
                'text': chunk,
                'metadata': {
                    'url': url,
                    'title': f"{title}_{i}",
                    'date': DATE.get_now_month_day_year_str(),
                    'topic': topic
                }
            }
            documents.append(doc)
        self.add_documents(collection, documents)
        print(f"Successfully imported {len(documents)} documents from {url} into ChromaDB.")

    def __create_documents_v2(self, collection, text, file_path, topic):
        documents = self.prepare_raw_text(text, os.path.basename(file_path), topic)
        self.add_documents(collection, documents)

    # Step 3: Create ChromaDB documents from the list of strings.
    def __create_documents(self, collection, text, file_path, topic:str=""):
        chunks = TextCleaner.split_string_by_limit(text, char_limit=self.character_limit)
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                'id': f"{os.path.basename(file_path)}_{i}",
                'text': chunk,
                'metadata': {
                    'url': file_path,
                    'title': os.path.basename(file_path),
                    'date': DATE.get_now_month_day_year_str(),
                    'topic': topic
                }
            }
            documents.append(doc)
        self.add_documents(collection, documents)
        print(f"Successfully imported {len(documents)} documents from {file_path} into ChromaDB.")

    def import_file(self, file_path, collection_name, topic=""):
        """Imports a .txt file and adds its contents to ChromaDB."""
        self.set_collection(collection_name)
        # Step 6: Call each inner function step by step.
        if file_path.endswith(".jsonl"):
            return self.__import_jsonl_file('website', file_path, collection_name, topic)
        else:
            text_content = read_file(file_path)
            if not text_content:
                print("No content to process.")
                return
            self.__create_documents(collection_name, text_content, file_path, topic)

    def __import_jsonl_file(self, id, file_path, collection_name, topic=""):
        """Imports a .jsonl file and adds its contents to ChromaDB."""
        self.set_collection(collection_name)
        # Step 6: Call each inner function step by step.
        objs = read_jsonl_file(file_path)
        for obj in objs:
            url = obj['url']
            title = obj['title']
            text_content = obj['content']
            if not text_content:
                print("No content to process.")
                return
            self.__create_jsonl_documents(collection_name, id=id, text=text_content, url=url, title=title, topic=topic)

    def import_directory(self, directory, collection_name, topic=""):
        files = []
        for file_path in self.__yield_file_paths(directory):
            if file_path.endswith(".DS_Store"):
                continue
            elif file_path.endswith(".jsonl"):
                self.__import_jsonl_file('website', file_path, collection_name, topic)
                files.append(file_path)
            else:
                self.import_file(file_path, collection_name, topic)
                files.append(file_path)
            time.sleep(1)
        print(f"Successfully imported {len(files)} files.")

    def __yield_file_paths(self, directory):
        """Yield the full file path for each file in the given directory."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                yield os.path.join(root, file)


if __name__ == '__main__':
    from config.RaiModels import RAI_MODs
    # collection = RAI_MODs['medical-neuro:latest']['collection']
    collection = RAI_MODs['ussf:latest']['collection']
    ftoc = FileToChromaConverter(collection_name=collection)
    ftoc.import_directory("/Users/chazzromeo/Desktop/ussfTrainingData", collection, 'national development model')
    # ftoc.import_directory("/Users/chazzromeo/ChazzCoin/MedRefs/files/pending/mian-neurosurgery", collection, 'neurosurgery')
    # ftoc.import_file("/Users/chazzromeo/Desktop/ParkCityTrainingData/Veo Camera System Instructions.pdf", collection, 'veo help support')