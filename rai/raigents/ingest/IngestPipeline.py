
from abc import abstractmethod, ABC
from typing import List

from rai.assistant.connectors import RaiAi
from rai.ingest.IngestModels import IngestBrief, IngestPage
from rai.ingest.loaders.rai_loaders.BaseLoad import RaiLoaderDocument
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.raigents.ingest.IngestContentAgent import IngestContentAgent
from rai.raigents.ingest.IngestDocumentCreator import IngestDocumentCreator
from rai.raigents.ingest.IngestSourceAgent import IngestSourceAgent

INGEST_PIPELINES = {}


def register_ingest_pipeline(name: str):
    def decorator(cls):
        INGEST_PIPELINES.setdefault(name, []).append(cls)
        return cls

    return decorator


class RaiIngestPipeline(ABC, RaiAi, TextProcessor):
    name = None

    briefs: List[IngestBrief] = []
    pages: List[IngestPage] = []
    docs: List[RaiLoaderDocument] = []

    @classmethod
    def get_registry(cls): return INGEST_PIPELINES

    @classmethod
    def pipeline(cls, name: str, data):
        agent_classes = INGEST_PIPELINES.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(data)

    @abstractmethod
    def type(self): pass
    @abstractmethod
    def parse(self, result): pass
    @abstractmethod
    def run(self, data): pass

    def get_briefs(self, data) -> List['IngestBrief']:
        bs = IngestSourceAgent.load_data(data).run()
        self.briefs.extend(bs)
        return bs

    def to_pages(self, briefs:List['IngestBrief']) -> List['IngestPage']:
       self.pages = IngestContentAgent.executes(briefs=briefs)
       return self.pages

    def to_docs(self, pages: List['IngestPage']) -> List['RaiLoaderDocument']:
       self.docs = IngestDocumentCreator.executes(pages=pages)
       return self.docs


"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
- remove term of service issues
- summarize data
- 
"""
@register_ingest_pipeline("docs")
class IngestPipelineDocuments(RaiIngestPipeline):
    def type(self): return "embed"
    def parse(self, result): return result

    def run(self, data):
        """ 1. Source Provider """
        self.get_briefs(data)

        """ 2. Content Agent """
        self.to_pages(self.briefs)

        """ 3. Document Creator """
        self.to_docs(self.pages)

        return self.docs




if __name__ == "__main__":
    # from rai.ingest.utilities.text_data import schedule_text
    pdf_file_path = "/Users/chazzromeo/Desktop/DocumentTestSet/instructions-1.pdf"
    website = "https://www.parkcitysoccer.org"
    pipe = "docs"
    docs = RaiIngestPipeline.pipeline(name=pipe, data=website)
    print(docs)
