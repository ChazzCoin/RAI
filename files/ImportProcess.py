import os
import re

from traits.trait_types import self

from files.importers import convert_files_to_txt
from files.FilePath import FilePath
from assistant.openai_client import chat_request
from assistant.rag import RAGWithChroma
from files.read import read_file
from F import OS
import json
import openai
import time
import threading
from typing import List, Dict, Any
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

    def _system_prompt2(self):
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

    def _system_prompt(self) -> str:
        return (
            "You are an AI assistant tasked with creating training data for fine-tuning an AI model. "
            "For each document provided, generate a set of question-and-answer pairs based on the content. "
            "The answers should be long, thorough, and informative. Format the output as a JSONL where each line "
            "is a JSON object with 'prompt' and 'completion' keys suitable for OpenAI fine-tuning."
        )

    def _verify_format(self, response: str) -> bool:
        try:
            lines = response.strip().split('\n')
            for line in lines:
                json_obj = json.loads(line)
                if 'prompt' not in json_obj or 'completion' not in json_obj:
                    return False
            return True
        except json.JSONDecodeError:
            return False

    def _format_response(self, response: str) -> str:
        # Attempt to correct formatting issues
        try:
            lines = response.strip().split('\n')
            formatted_lines = []
            for line in lines:
                json_obj = json.loads(line)
                formatted_lines.append(json.dumps(json_obj, ensure_ascii=False))
            return '\n'.join(formatted_lines)
        except json.JSONDecodeError as e:
            print(f"Formatting error: {e}")
            return ""

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
                assistant_reply = chat_request(self._system_prompt2(), document['content'], model="gpt-4o-mini")
                print(assistant_reply)
                # extractor(assistant_reply, self.output_file)
                # write_strings_to_jsonl(results, self.output_file)
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
        threads = []
        for document in self.documents:
            self._process_document(document)
            # thread = threading.Thread(target=self._process_document, args=(document,))
            # thread.start()
            # threads.append(thread)
            # time.sleep(1)  # Throttle requests to avoid hitting rate limits

        # for thread in threads:
        #     thread.join()

        print("All documents have been processed.")

    def start(self):
        self.process_documents()
def extractor(text, output_file):
    pattern = r'(\{"messages":\s*\[.*?\]\s*\})'
    matches = re.findall(pattern, text, re.DOTALL)
    valid_json_objects = []
    for match in matches:
        try:
            # obj = json.loads(match)
            valid_json_objects.append(match)
        except json.JSONDecodeError:
            continue  # Skip invalid JSON
    write_strings_to_jsonl(valid_json_objects, output_file)
    return valid_json_objects
# def extractor(text):
#     objs = []
#     start = 0
#     for currentIndex in text:
#         char = text[currentIndex]
#         char_1 = text[currentIndex + 1]
#         char_2 = text[currentIndex + 2]
#         if char == '{' and char_1 == "\"" and char_2 == "m":
#             start = currentIndex
#         elif char == '}' and char_1 == "]" and char_2 == "}":
#             temp_obj = text[start:currentIndex + 2]
#             objs.append(temp_obj)
#         currentIndex += 1
#     return objs

def write_strings_to_jsonl(strings_list, output_file):
    with open(output_file, 'a', encoding='utf-8') as f:
        for s in strings_list:
            f.write(s + '\n')

def find_matching_objects(text):
    def split_json_objects(s):
        json_objects = []
        brace_level = 0
        current_obj = ''
        in_string = False
        escape = False
        for i, c in enumerate(s):
            current_obj += c
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == '{':
                    brace_level += 1
                elif c == '}':
                    brace_level -= 1
                if brace_level == 0 and current_obj.strip():
                    json_objects.append((current_obj.strip(), i))
                    current_obj = ''
        return json_objects
    # Remove any leading/trailing whitespace
    text = text.strip()
    # Extract potential JSON objects from the text
    potential_objects = split_json_objects(text)
    matching_objects = []
    for obj_str, end_idx in potential_objects:
        matching_objects.append(obj_str)
        # try:
        #     obj = json.loads(obj_str)
        # except json.JSONDecodeError:
        #     continue  # Skip invalid JSON objects
        # # Check if the object matches the required format
        # if is_matching_format(obj):
        #     matching_objects.append(obj)
    return matching_objects

def is_matching_format(obj):
    # Check if the object is a dictionary with 'messages' as the only key
    if not isinstance(obj, dict) or set(obj.keys()) != {'messages'}:
        return False
    messages = obj['messages']
    # Check if 'messages' is a list with exactly 3 items
    if not isinstance(messages, list) or len(messages) != 3:
        return False
    # Define the expected roles in order
    expected_roles = ['system', 'user', 'assistant']
    for message, expected_role in zip(messages, expected_roles):
        # Check if each message is a dictionary
        if not isinstance(message, dict):
            return False
        # Check for 'role' and 'content' keys
        if set(message.keys()) != {'role', 'content'}:
            return False
        # Check if the 'role' matches the expected role
        if message['role'] != expected_role:
            return False
        # 'content' can be any text, so we don't need to check its value
    return True

if __name__ == '__main__':
    # ImportProcessor.process_raw_files()
    ToTrainingData(
        "/Users/chazzromeo/ChazzCoin/MedRefs/extractors/output/www_parkcitysoccer_org.json",
        "/Users/chazzromeo/ChazzCoin/MedRefs/extractors/output/parkcitysoccer.jsonl"
    ).start()