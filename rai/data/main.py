from rai.agents.PromptBaseLoader import PromptRegistry
from rai.data import RaiPath
from rai.data.extraction.read import read_file
from rai.data.extraction.RaiFileExtraction import RaiFileExtractor, RaiConfig
from rai.data.extraction.RaiWebExtraction import RaiWebExtractor
from rai.data.loaders.rai_loaders.RaiMetadataLoader import RaiMetadataLoader

RAI_DBs = lambda db: (f"{db}-main", f"{db}-internal", f"{db}-development")

def delete_collects(*collections):
    RaiFileExtractor.delete_collections(*collections)

"""
Pipelines:
1. 'chroma' = Will import documents into ChromaDB
2. 'print' = Will print/log all documents for debugging purposes
"""

def get_prompt(category='autoformat', prompt_name='base_format_prompt', *args):
    """ args = ("arg one", "arg two") """
    return PromptRegistry.get(category, prompt_name, args)

def run_auto_import(fig:RaiConfig):
    return RaiFileExtractor.fromConfig(fig).run()

def scrape_site(url:str, pages=0):
    """ pages = 0 -> entire website """
    RaiWebExtractor.save(url, page_limit=pages)

def open_file(file_path, enable_vision=False): return read_file(file_path, enable_vision=enable_vision)

def find_directory(file_name): pass
def find_file(file_name): pass

if __name__ == '__main__':
    config = RaiConfig()
    config.pipeline = RaiFileExtractor.Pipelines.CHROMA
    config.generate_ai_metadata = True
    config.overwrite = True
    config.base_path = RaiPath("/Users/chazzromeo/Desktop/data")
    config.collection_prefix = "parkone"
    run_auto_import(fig=config)