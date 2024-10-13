from rai.agents.PromptBaseLoader import PromptRegistry
from rai.data import RaiPath
from rai.data.extraction.read import read_file
from rai.data.extraction.RaiFileExtraction import RaiFileExtractor, RaiConfig
from rai.data.extraction.RaiWebExtraction import RaiWebExtractor

RAI_DBs = lambda db: (f"{db}-main", f"{db}-internal", f"{db}-development")

def delete_collects(*collections):
    RaiFileExtractor.delete_collections(*collections)

"""
Pipelines:
1. 'chroma' = Will import documents into ChromaDB
2. 'print' = Will print/log all documents for debugging purposes
"""


"""

prompt = get_prompt('soccer', 'get_system_prompt', ())
prompt = get_prompt('metadata', 'get_ai_extraction_prompt', ())
"""
def get_prompt(category='autoformat', prompt_name='base_format_prompt', *args):
    """ args = ("arg one", "arg two") -> a tuple() of arguments"""
    return PromptRegistry.get(category, prompt_name, args)
def list_prompt_categories():
     print(PromptRegistry.get_all_types())

"""
    config = RaiConfig()
    config.pipeline = RaiFileExtractor.Pipelines.CHROMA
    config.generate_ai_metadata = True
    config.overwrite = True
    config.base_path = RaiPath("/Users/chazzromeo/Desktop/data")
    config.collection_prefix = "parkone"
    run_rai_file_extraction(fig=config)
"""
def run_rai_file_extraction(fig:RaiConfig):
    return RaiFileExtractor.fromConfig(fig).run()

def run_rai_web_extraction(url:str, pages=0):
    """ pages = 0 -> entire website """
    RaiWebExtractor.save(url, page_limit=pages)

""" 
    Basic ole file opener for most file types youll need. 
    Returns a string of the text.
    Otherwise, you'll need the RaiFileExtractor for a more robust extraction process. 
"""
def open_file(file_path, enable_vision=False): return read_file(file_path, enable_vision=enable_vision)

def find_directory(file_name): pass
def find_file(file_name): pass

if __name__ == '__main__':
    print(PromptRegistry.list_prompts_by_category('metadata'))
    # list_prompt_categories()
    # config = RaiConfig()
    # config.pipeline = RaiFileExtractor.Pipelines.CHROMA
    # config.generate_ai_metadata = True
    # config.overwrite = True
    # config.base_path = RaiPath("/Users/chazzromeo/Desktop/data")
    # config.collection_prefix = "parkone"
    # run_rai_file_extraction(fig=config)