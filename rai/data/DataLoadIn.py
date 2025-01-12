from F import LIST, DATE
from rai.data.utilities.TextUtils import TextProcessor
from rai.data.files.write import write_to_jsonl, write_to_json
from rai.internal.connectors import VECTOR_DB_CLIENT

DATA_CLEANER = lambda text: TextProcessor.clean_text_for_openai_embedding(text)

PRETRAIN = lambda text: { "text": DATA_CLEANER(text) }

FINETUNE = lambda system, user, assistant: {
    "messages": [
        {"role": "system", "content": DATA_CLEANER(system)},
        {"role": "user", "content": DATA_CLEANER(user)},
        {"role": "assistant", "content": DATA_CLEANER(assistant)},
    ]
}

"""
**FORMAT AND CLEAN DATA**
- Grammar Check.
- Spell Check.
- Remove Unwanted Characters/Bad Characters.
- Remove any text/data that would breach or go against OpenAI Terms of Service

**ENHANCE DATA**
- 
"""

""" Step 1. Get and Format Data Structure """
class DataFromChroma:
    output_type = 'json'
    prefix = ""
    output_file = ""
    raw_data = []
    prepared_data = []

    def __init__(self, prefix, output_file=None, output_type='json'):
        self.output_file = output_file
        self.output_type = output_type
        self.get_set_raw_data(prefix)

    def get_set_raw_data(self, prefix):
        collections = VECTOR_DB_CLIENT.get_all_collections_by_chain(prefix)
        for collection in collections:
            docs = VECTOR_DB_CLIENT.get(collection)
            for doc in docs.documents:
                if type(doc) in [list, tuple]:
                    for item in doc:
                        self.raw_data.append(item)
                elif type(doc) in [str]:
                    self.raw_data.append(doc)
                else:
                    self.raw_data.append(str(doc))
        self.raw_data = LIST.flatten(self.raw_data)
        return self.raw_data

    def get_pretrain_data(self):
        for doc in self.raw_data:
            if type(doc) in [list, tuple]:
                for item in doc:
                    self.prepared_data.append(PRETRAIN(item))
            elif type(doc) in [str]:
                self.prepared_data.append(PRETRAIN(doc))
            else:
                self.prepared_data.append(PRETRAIN(doc))
        self.save_to_file()
        return self.prepared_data

    def save_to_file(self):
        if not self.output_file: return
        if self.output_type == 'json':
            write_to_json(self.prepared_data, self.output_file)
        elif self.output_type == 'jsonl':
            for item in self.prepared_data:
                write_to_jsonl(item, file_path=file_name)


if __name__ == '__main__':
    file_name = f"/Users/chazzromeo/Desktop/pcsc2024/pre_train_{DATE.get_now_month_day_year_str()}"
    DataFromChroma("pcsc2024.general", output_file=file_name).get_pretrain_data()