import os
import json
import openai
import time
import threading
from typing import List, Dict, Any
from rai.assistant.openai_client import openai_generate


class ToTrainingData:
    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
        self.data_lock = threading.Lock()
        self.documents = self._load_documents()
        # self.session = requests.Session()

    def _load_documents(self) -> List[Dict[str, Any]]:
        documents = []
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file '{self.input_file}' not found.")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    doc = json.loads(line)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
        return documents

    def _system_prompt(self):
        return """
        You are now my Dataset Training and Format Expert. 
        I will provide you with raw datasets and you will do the following.

        RULES:
        1. You will read the data and you will come up with 5-10 questions that can be answered using the dataset.
        2. You will give long detailed answers.
        3. You will format the response and the questions/answers based on jsonl openai fine-tuning training data format.
        4. You will ONLY return the jsonl data.
        5. Remove any ```jsonl ``` you might want to add. I don't want it.
        
        **PRIORITIZE THE RESPONSE FORMAT ABOVE ALL ELSE**

        Example Format: 
        {"messages": [{"role": "system", "content": "You will answer my question based on the information at hand." }, {"role": "user", "content": "Question?"}, {"role": "assistant", "content": "Answer to the question..."}]}
        {"messages": [{"role": "system", "content": "You will answer my question based on the information at hand." }, {"role": "user", "content": "Question?"}, {"role": "assistant", "content": "Answer to the question..."}]}
        """

    def _save_to_file(self, content: str):
        with self.data_lock:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(content)
                f.write('\n')

    def _process_document(self, document: Dict[str, Any]):
        max_retries = 5
        backoff_factor = 2
        retry_count = 0

        while retry_count < max_retries:
            try:
                assistant_reply = openai_generate(self._system_prompt(), document['content'], model="gpt-4o-mini")
                self._save_to_file(assistant_reply)
                print(f"Processed document from URL: {document['url']}")
                break
            except openai.RateLimitError:
                retry_count += 1
                sleep_time = backoff_factor ** retry_count
                print(f"Rate limit exceeded. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            except openai.OpenAIError as e:
                print(f"OpenAI API error: {e}")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                break

    def process_documents(self):
        for document in self.documents:
            self._process_document(document)

    def process_documents_async(self):
        threads = []
        for document in self.documents:
            thread = threading.Thread(target=self._process_document, args=(document,))
            thread.start()
            threads.append(thread)
            time.sleep(1)
        for thread in threads:
            thread.join()

        print("All documents have been processed.")

    def start(self):
        self.process_documents()


if __name__ == '__main__':
    ToTrainingData(
        "/extractors/output/www_parkcitysoccer_org1.json",
        "/extractors/output/parkcitysoccer.jsonl"
    ).start()