from abc import abstractmethod, ABC
from typing import List

from F import LIST

from rai.agentic.ai_assistants.QCache import VectorCache
from rai.agentic.ai_assistants.QStore import VectorStore
from rai.assistant.connectors import rAI
from rai.ingest.IngestModels import IngestRecord
from rai.ingest.loaders.rai_loaders.BaseLoad import IngestLoaderDocument
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.agentic.ingest.IngestNLPAgent import IngestNLPAgent
from rai.agentic.ingest.IngestDocumentCreator import IngestDocumentCreator
from rai.agentic.ingest.IngestSourceAgent import IngestSourceAgent

INGEST_PIPELINES = {}


def register_ingest_pipeline(name: str):
    def decorator(cls):
        INGEST_PIPELINES.setdefault(name, []).append(cls)
        return cls

    return decorator


class rIngestWorkFlow(ABC, rAI, TextProcessor):
    name = None
    prefix = None

    vector_store = VectorStore()
    vector_cache = VectorCache()

    record: IngestRecord = IngestRecord()

    briefs: {} = {}
    pages: {} = {}
    docs: List[IngestLoaderDocument] = []

    @classmethod
    def get_registry(cls): return INGEST_PIPELINES

    @classmethod
    def pipeline(cls, name: str, data, prefix=None):
        agent_classes = INGEST_PIPELINES.get(name)
        if not agent_classes: return None
        cls.name = name
        cls.prefix = prefix
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(data)

    @abstractmethod
    def type(self): pass
    @abstractmethod
    def parse(self, result): pass
    @abstractmethod
    def run(self, data): pass

    def get_all_briefs(self, datas) -> {}:
        self.briefs = IngestSourceAgent.executes(datas)
        return self.briefs

    def get_briefs(self, data) -> {}:
        if type(data) is list:
            self.get_all_briefs(data)
        else:
            self.briefs = IngestSourceAgent.execute(data)
            return self.briefs

    def to_pages(self, briefs: {}) -> {}:
       self.pages = IngestNLPAgent.executes(name=self.name, briefs=briefs)
       return self.pages

    def create_and_attach_docs(self, pages: {}) -> {}:
       self.pages = IngestDocumentCreator.executes(pages=pages)
       return self.pages

    def get_all_docs(self) -> {}:
       for k,v in self.pages.items():
           temp = list(v.loader_documents)
           self.docs.extend(temp)
       return LIST.flatten(self.docs)

    def add_to_store(self) -> {}: return self.vector_store.stores(self.prefix, self.docs)
    def add_to_cache(self): return self.vector_cache.caches(self.prefix, self.docs)

"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
- remove term of service issues
- summarize data
- 
"""
@register_ingest_pipeline("injection")
class IngestPipelineDocuments(rIngestWorkFlow):
    def type(self): return "ai"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)
        """ 2. Content Agent """
        self.to_pages(self.briefs)
        """ 3. Document Creator """
        self.create_and_attach_docs(self.pages)
        """ 4. Get All Documents """
        self.get_all_docs()
        return self.docs
@register_ingest_pipeline("briefs")
class IngestPipelineBriefs(rIngestWorkFlow):
    def type(self): return "briefs"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        return self.get_briefs(data)
@register_ingest_pipeline("pages")
class IngestPipelinePages(rIngestWorkFlow):
    def type(self): return "pages"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)
        """ 2. Content Agent """
        return self.to_pages(self.briefs)

@register_ingest_pipeline("docs")
class IngestPipelineDocuments(rIngestWorkFlow):
    def type(self): return "embed"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)
        """ 2. Content Agent """
        self.to_pages(self.briefs)
        """ 3. Document Creator """
        self.create_and_attach_docs(self.pages)
        """ 4. Get All Documents """
        self.get_all_docs()
        return self.docs

@register_ingest_pipeline("multi-docs")
class IngestPipelineMultiDocuments(rIngestWorkFlow):
    def type(self): return "embed"
    def parse(self, result): return result

    def run(self, data):
        """ 1. Source Provider """
        if type(data) is list:
            self.get_all_briefs(data)
        else:
            self.get_briefs(data)
        """ 2. Content Agent """
        self.to_pages(self.briefs)
        """ 3. Document Creator """
        self.create_and_attach_docs(self.pages)
        """ 4. Get All Documents """
        self.get_all_docs()
        return self.docs

@register_ingest_pipeline("store")
class IngestPipelineStoreDocuments(rIngestWorkFlow):
    def type(self): return "store"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)
        """ 2. Content Agent """
        self.to_pages(self.briefs)
        """ 3. Document Creator """
        self.create_and_attach_docs(self.pages)
        """ 4. Get All Documents """
        self.get_all_docs()
        """ 5. Save to Storage """
        return self.add_to_store()

@register_ingest_pipeline("cache")
class IngestPipelineCacheDocuments(rIngestWorkFlow):
    def type(self): return "cache"
    def parse(self, result): return result
    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)
        """ 2. Content Agent """
        self.to_pages(self.briefs)
        """ 3. Document Creator """
        self.create_and_attach_docs(self.pages)
        """ 4. Get All Documents """
        self.get_all_docs()
        """ 5. Save to Storage """
        return self.add_to_cache()

if __name__ == "__main__":
    # from rai.ingest.utilities.text_data import schedule_text
    pdf_file_path = "/Users/chazzromeo/Desktop/portal/docs/Neuro101.pdf"
    website = "https://www.parkcitysoccer.org/tournaments"
    pipe = "store"
    prefix = 'rai2025.3'
    docs = rIngestWorkFlow.pipeline(name=pipe, data=pdf_file_path, prefix=prefix)
    print(docs)
