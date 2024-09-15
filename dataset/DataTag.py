from enum import Enum
from F.LOG import Log
import re
Log = Log("DataTag")

TAG_ID = lambda id: f"|{id}|"
TAG = lambda id, data: f"|{id}| {data} |{id}|"


class DataTag:
    URL = "url"
    FILE = "file"
    TITLE = "title"
    DATE = "date"

    @staticmethod
    def insert_tag(text: str, tag_data: str, tag_id: str):
        return f"{TAG(tag_id, tag_data)} \n {text}"

    @staticmethod
    def append_tag(text: str, tag_data: str, tag_id: str):
        return f"{text} \n {TAG(tag_id, tag_data)}"

    @staticmethod
    def extract_tag_data(text, tag_id):
        start_index = text.find(TAG_ID(tag_id))
        if start_index == -1:
            return "Start tag not found"
        start_index += len(TAG_ID(tag_id))
        stop_index = text.find(TAG_ID(tag_id), start_index)
        if stop_index == -1:
            return "End tag not found."
        return text[start_index:stop_index].strip()

    @staticmethod
    def remove_tag(text, tag_id):
        pattern = re.escape(TAG_ID(tag_id)) + r'.*?' + re.escape(TAG_ID(tag_id))
        return re.sub(pattern, '', text, flags=re.DOTALL)

if __name__ == '__main__':
    test = "akjsndfoansdfonasdouifnasdof asodifjasoidjfoaisdjfoias jdfoiajs dofijasdoifjasodifjaosidjfaoisdjfoiasjdfoiawj"
    testin = DataTag.insert_tag(test, "www.url.com", "url")
    print(testin)
    # testout = DataTag.extract_tag_data(testin, "url")
    # print(testout)
    out = DataTag.remove_tag(testin, "url")
    print(out)