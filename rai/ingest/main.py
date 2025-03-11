from F import DICT, LIST

from rai.agentic.ai_flows.r_flows import rFlows
from rai.ingest.files.read import read_file
from rai.ingest.DataImport import RaiDataImporter, RaiDataImportConfig
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
    config.base_path = "/Users/chazzromeo/Desktop/pcsc2025/PARKING GUIDELINES 2024 - Google Docs.pdf"
    config.url = None #"https://playmetrics.com/teams/194123/summary"
    config.username = "jperson@parkcitysoccer.org"
    config.password = "Philly23!"
    config.page_limit = 500
    importer = RaiDataImporter()
    importer.setup(config)
    importer.import_file(config.base_path)

def main(name, prefix, user_prompt):
    # from rai.pipeline.utilities.text_data import schedule_text
    results = rFlows.flow(
            name=name,
            prefix=prefix,
            user_prompt=user_prompt
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)


if __name__ == "__main__":
    from rai.ingest.utilities.text_data import schedule_text
    user_prompt = "I wanna see the last 10 documents."
    main("knowledge_flow", prefix="rai2025.1", user_prompt=user_prompt)

# if __name__ == '__main__':
#     run_import()
    # get_all("pcsc2025.3.web.locations")
    # list_all_collections_by_prefix("pcsc2025", "3")