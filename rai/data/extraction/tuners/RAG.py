from nlp.Utils import remove_special_characters
from rai.data.extraction.write import write_to_jsonl
from rai.data.loaders.rai_loaders.Utils import remove_excess_newlines
from rai.internal.connectors import VECTOR_DB_CLIENT


JSONL = lambda prompt, completion: {
    "messages": [
        { "role": "system", "content": prompt },
        { "role": "assistant", "content": completion }
    ]
}

SYS = """
You are the all knowing knowledge base for Park City Soccer Club.
You will learn and understand everything about Park City Soccer Club and Youth Soccer Clubs.
**When asked about Park City Soccer Club, you will return the best possible results based on the context of the users input.**
"""


class KnowledgeBaseFineTuner:
    completions = []

    def run(self):
        collections = VECTOR_DB_CLIENT.get_all_collections_by_chain("pcsc2024")
        for collection in collections:
            docs = VECTOR_DB_CLIENT.get(collection)
            for doc in docs.documents:
                if type(doc) in [list, tuple]:
                    for item in doc:
                        item = remove_excess_newlines(item)
                        item = remove_special_characters(item)
                        self.completions.append(JSONL(SYS, item))
                elif type(doc) in [str]:
                    self.completions.append(JSONL(SYS, doc))
                else:
                    print(doc)
        self.post_run()

    def post_run(self):
        for item in self.completions:
            write_to_jsonl(item, "/Users/chazzromeo/Desktop/pcsc2024/fine_tuner.jsonl")


KnowledgeBaseFineTuner().run()