from F import DICT, LIST
from rai.data.files.read import read_file
from rai.data.DataImport import RaiDataImporter, RaiDataImportConfig
from rai.internal.connectors import VECTOR_DB_CLIENT

def delete_collects(*collections):
    RaiDataImporter.delete_collections(*collections)

def get_all(collection):
    for i in LIST.flatten(RaiDataImporter.get_all_from_collection(collection)):
        for doc in DICT.get("documents", i, []):
            if type(doc) in [list, tuple]:
                for d in doc:
                    print(d)
            else:
                print(doc)

def open_file(file_path, enable_vision=False): return read_file(file_path, enable_vision=enable_vision)

def find_directory(file_name): pass
def find_file(file_name): pass

def list_all_collections_by_prefix(*chained_path:str):
    temp = VECTOR_DB_CLIENT.get_all_collections_by_chain(*chained_path)
    print("Collections:\n", temp)
    return temp

def run_import():
    config = RaiDataImportConfig()
    config.pipeline = RaiDataImportConfig.Pipelines.CHROMA
    config.generate_metadata = False
    config.generate_collection_name = False
    config.overwrite = False
    config.single_run = True
    config.collection_prefix = "pcsc2025.3"
    config.base_path = None#"/Users/chazzromeo/Desktop/pcsc2025"
    config.url = "https://www.parkcityextremecup.com/"
    config.username = None
    config.password = None
    config.page_limit = 500
    RaiDataImporter.run(config)

if __name__ == '__main__':
    # print(PromptRegistry.list_prompts_by_category('metadata'))
    # list_prompt_categories()
    # list_all_collections_by_prefix("pcsc2025", "2")
    # collects = VECTOR_DB_CLIENT.client.list_collections()
    # for c in collects:
    #     print(c)
    # all = VECTOR_DB_CLIENT.get_all_collections_by_chain("pcsc2025")
    # for collection in all:
    #     VECTOR_DB_CLIENT.delete_collection(collection)

    run_import()
    # get_all("pcsc2025.web")