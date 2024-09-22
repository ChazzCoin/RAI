import os
from dataset.TextCleaner import TextCleaner
from F import DATE
from assistant.rag import RAGWithChroma
from files.read import read_file


""" MASTER """
class FileToChromaConverter(RAGWithChroma):
    character_limit = 1500

    # Step 3: Create ChromaDB documents from the list of strings.
    def create_documents(self, text, file_path, topic:str=""):
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
        self.add_documents(documents)
        print(f"Successfully imported {len(documents)} documents from {file_path} into ChromaDB.")

    def import_file(self, file_path, collection_name, topic=""):
        """Imports a .txt file and adds its contents to ChromaDB."""
        self.set_collection(collection_name)
        # Step 6: Call each inner function step by step.
        text_content = read_file(file_path)
        if not text_content:
            print("No content to process.")
            return
        self.create_documents(text_content, file_path, topic)

    def import_directory(self, directory, collection_name, topic=""):
        for file_path in self.yield_file_paths(directory):
            self.import_file(file_path, collection_name, topic)

    def yield_file_paths(self, directory):
        """Yield the full file path for each file in the given directory."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                yield os.path.join(root, file)


if __name__ == '__main__':
    ftoc = FileToChromaConverter()
    ftoc.import_directory("/Users/chazzromeo/ChazzCoin/MedRefs/files/pending/mian-neurosurgery", 'neuro')
