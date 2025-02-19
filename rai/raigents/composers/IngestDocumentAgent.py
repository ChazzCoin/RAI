from abc import abstractmethod

from rai.ingest.loaders.rai_loaders.BaseLoad import RaiBaseLoader, RaiLoaderDocument
from rai.ingest.utilities.DataUtilities import ensure_string_for_chroma
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.utilities.text_data import schedule_text
from rai.ingest.web.WebModels import PageAnalysisModel

from F.LOG import Log

from rai.raigents.composers.IngestContentAgent import IngestContentAgent

Log = Log("composers.DocumentCreatorAgent")

from typing import List, Dict, Any
import json

class RaiGent:

    @abstractmethod
    def pipeline(self, name, user_prompt, system_prompt, image): pass


class IngestDocumentAgent(RaiBaseLoader, TextProcessor):
    """
    A condensed document creator that processes a PageAnalysisModel and creates
    a single document for each logical grouping (content, NLP, FNLP, agent, images,
    contacts, locations, tables, events).
    """
    page = None
    cache: List['RaiLoaderDocument'] = []
    documents: List['RaiLoaderDocument'] = []

    def __init__(self):
        super().__init__(file_path="")

    @classmethod
    def execute(cls, content: str, image=None, **metadata):
        page: PageAnalysisModel = IngestContentAgent.execute(content, image, **metadata)
        self = cls()
        self.load_page(page)
        return self.process()

    def load_page(self, page: PageAnalysisModel):
        self.page = page

    def are_docs_identical(self, doc1: 'RaiLoaderDocument', doc2: 'RaiLoaderDocument') -> bool:
        return (self.are_strings_identical(doc1.page_content, doc2.page_content) and
                self.are_dicts_identical(doc1.metadata, doc2.metadata))

    def has_doc(self, doc: 'RaiLoaderDocument') -> bool:
        for document in self.cache:
            if self.are_docs_identical(document, doc):
                return True
        return False

    def add_doc(self, content: str, metadata: Dict[str, Any], collection: str) -> None:
        """
        Clean and optionally split the text (if it exceeds limits), add a collection
        label to the metadata, and store the document if not a duplicate.
        """
        meta = metadata.copy()
        meta['collection'] = collection

        cleaned_content = self.TEXT_CLEANER(str(content))
        if not self.string_length_is_within(text=cleaned_content, max_length=5000):
            content_parts = self.split_string_by_limit(cleaned_content, char_limit=5000)
        else:
            content_parts = [cleaned_content]

        for part in content_parts:
            doc = RaiLoaderDocument(
                page_content=part,
                metadata=ensure_string_for_chroma(meta)
            )
            if self.has_doc(doc):
                continue
            self.cache.append(doc)
            self.documents.append(doc)

    def process(self) -> List['RaiLoaderDocument']:
        """
        Combines the various fields in the PageAnalysisModel into condensed documents.
        """
        base_metadata = self.page.details.model_dump() if self.page.details else {}
        Log.i("Creating content document. -> [ pages ]")
        self.add_doc(self.page.content, base_metadata, "pages")

        # --- Combine Content Fields ---
        content_parts = []
        if self.page.content_extended:
            content_parts.append("Extended Content:\n" + self.page.content_extended)
        if self.page.sub_content:
            content_parts.append("Sub Content:\n" + "\n".join(self.page.sub_content))
        combined_content = "\n\n".join(content_parts)
        if combined_content.strip():
            Log.i("Creating combined content document.")
            self.add_doc(combined_content, base_metadata, "content")

        # --- Combine NLP Fields (NLPAssistantModel) ---
        nlp_parts = []
        if self.page.nlp:
            nlp = self.page.nlp
            if nlp.summary:
                nlp_parts.append("Summary:\n" + json.dumps(nlp.summary))
            if nlp.sentences:
                nlp_parts.append("Sentences:\n" + " ".join(nlp.sentences))
            if nlp.paragraphs:
                nlp_parts.append("Paragraphs:\n" + "\n".join(nlp.paragraphs))
            if nlp.pos_tags:
                nlp_parts.append("POS Tags:\n" + str(nlp.pos_tags))
            if nlp.named_entities:
                nlp_parts.append("Named Entities:\n" + str(nlp.named_entities))
            if nlp.lemmas:
                nlp_parts.append("Lemmas:\n" + " ".join(nlp.lemmas))
            if nlp.dependency_parse:
                nlp_parts.append("Dependency Parse:\n" + str(nlp.dependency_parse))
            if nlp.frequency_distribution:
                nlp_parts.append("Frequency Distribution:\n" + str(nlp.frequency_distribution))
            if nlp.urls:
                nlp_parts.append("URLs:\n" + ", ".join(nlp.urls))
            if nlp.sentiment:
                nlp_parts.append("Sentiment:\n" + str(nlp.sentiment))
        combined_nlp = "\n\n".join(nlp_parts)
        if combined_nlp.strip():
            Log.i("Creating combined NLP document.")
            self.add_doc(combined_nlp, base_metadata, "nlp")

        # --- Combine FNLP Fields (FNLPAssistantModel) ---
        fnlp_parts = []
        if self.page.fnlp:
            fnlp = self.page.fnlp
            if fnlp.sentences:
                fnlp_parts.append("Sentences:\n" + " ".join(fnlp.sentences))
            if fnlp.paragraphs:
                fnlp_parts.append("Paragraphs:\n" + "\n".join(fnlp.paragraphs))
            if fnlp.tags:
                fnlp_parts.append("Tags:\n" + ", ".join(fnlp.tags))
            if fnlp.addresses:
                fnlp_parts.append("Addresses:\n" + ", ".join(fnlp.addresses))
            if fnlp.urls:
                fnlp_parts.append("URLs:\n" + ", ".join(fnlp.urls))
            if fnlp.lines:
                fnlp_parts.append("Lines:\n" + " ".join(str(line) for line in fnlp.lines))
            if fnlp.top_words:
                fnlp_parts.append("Top Words:\n" + ", ".join(fnlp.top_words))
            if fnlp.words:
                fnlp_parts.append("Words:\n" + ", ".join(fnlp.words))
            if fnlp.bi_words:
                fnlp_parts.append("Bi Words:\n" + ", ".join(fnlp.bi_words))
            if fnlp.tri_words:
                fnlp_parts.append("Tri Words:\n" + ", ".join(fnlp.tri_words))
            if fnlp.quad_words:
                fnlp_parts.append("Quad Words:\n" + ", ".join(fnlp.quad_words))
            if fnlp.character_count is not None:
                fnlp_parts.append("Character Count:\n" + str(fnlp.character_count))
            if fnlp.word_count is not None:
                fnlp_parts.append("Word Count:\n" + str(fnlp.word_count))
            if fnlp.sentence_count is not None:
                fnlp_parts.append("Sentence Count:\n" + str(fnlp.sentence_count))
            if fnlp.paragraph_count is not None:
                fnlp_parts.append("Paragraph Count:\n" + str(fnlp.paragraph_count))
        combined_fnlp = "\n\n".join(fnlp_parts)
        if combined_fnlp.strip():
            Log.i("Creating combined FNLP document.")
            self.add_doc(combined_fnlp, base_metadata, "nlp")

        # --- Combine NLP Agent Fields ---
        agent_parts = []
        if self.page.nlp_agent:
            agent = self.page.nlp_agent
            if agent.summary:
                agent_parts.append("Summary:\n" + agent.summary)
            if agent.paraphrase:
                agent_parts.append("Paraphrase:\n" + agent.paraphrase)
            if agent.sentiment:
                agent_parts.append("Sentiment:\n" + str(agent.sentiment))
            if agent.queries:
                agent_parts.append("Queries:\n" + ", ".join(agent.queries))
            if agent.document_type:
                agent_parts.append("Document Types:\n" + ", ".join(agent.document_type))
            if agent.context_groups:
                agent_parts.append("Context Groups:\n" + " ".join(str(context) for context in agent.context_groups))
        combined_agent = "\n\n".join(agent_parts)
        if combined_agent.strip():
            Log.i("Creating combined NLP Agent document.")
            self.add_doc(combined_agent, base_metadata, "agent")

        # --- Combine Images ---
        image_parts = []
        if self.page.images:
            for image in self.page.images:
                # Use image content if available, otherwise the URL.
                if getattr(image, 'content', None):
                    image_parts.append(image.content)
                elif getattr(image, 'url', None):
                    image_parts.append(image.url)
        combined_images = "\n\n".join(image_parts)
        if combined_images.strip():
            Log.i("Creating combined Images document.")
            self.add_doc(combined_images, base_metadata, "images")

        # --- Combine Contacts ---
        if self.page.contacts:
            combined_contacts = "\n\n".join(str(contact) for contact in self.page.contacts)
            if combined_contacts.strip():
                Log.i("Creating combined Contacts document.")
                self.add_doc(combined_contacts, base_metadata, "contacts")

        # --- Combine Locations ---
        if self.page.locations:
            combined_locations = "\n\n".join(str(location) for location in self.page.locations)
            if combined_locations.strip():
                Log.i("Creating combined Locations document.")
                self.add_doc(combined_locations, base_metadata, "locations")

        # --- Combine Tables ---
        if self.page.tables:
            combined_tables = "\n\n".join(str(table) for table in self.page.tables)
            if combined_tables.strip():
                Log.i("Creating combined Tables document.")
                self.add_doc(combined_tables, base_metadata, "tables")

        # --- Combine Events ---
        if self.page.events:
            combined_events = "\n\n".join(str(event) for event in self.page.events)
            if combined_events.strip():
                Log.i("Creating combined Events document.")
                self.add_doc(combined_events, base_metadata, "events")

        Log.i(f"Total condensed documents created: {len(self.documents)}")
        return self.documents

if __name__ == "__main__":
    agent = IngestDocumentAgent()
    page_result = agent.execute(content=schedule_text)
    print(page_result)