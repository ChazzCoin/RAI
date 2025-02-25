
from F.LOG import Log
Log = Log("composers.DocumentCreatorAgent")

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from rai.assistant.connectors import RaiAi
from rai.ingest.IngestModels import IngestPage
from rai.ingest.loaders.rai_loaders.BaseLoad import RaiBaseLoader, IngestLoaderDocument
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.utilities.text_data import schedule_text

class IngestDocumentCreator(RaiBaseLoader, TextProcessor, RaiAi):
    """
    A condensed document creator that processes an IngestPage and creates
    a document for each logical grouping: pages (full content), parts (split
    page content if large), nlp (basic NLP content), agentnlp (AI agent based NLP),
    images, and tables.
    """
    page = None
    cache: List['IngestLoaderDocument'] = []
    documents: List['IngestLoaderDocument'] = []

    def __init__(self):
        super().__init__(file_path="")

    @classmethod
    def execute(cls, page: IngestPage) -> List['IngestLoaderDocument']:
        self = cls()
        self.load_page(page)
        return self.run()

    @classmethod
    def executes(cls, pages: {}) -> {}:
        def runner(page):
            instance = cls()
            instance.load_page(page)
            return instance.run()

        results = {}
        with ThreadPoolExecutor() as executor:
            # Submit all briefs for processing
            future_to_index = {
                executor.submit(runner, brief): index for index, brief in enumerate(pages.values())
            }
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    results[index] = None
                    print(f"Error processing brief at index {index}: {e}")
        sorted_items = sorted(results.items(), key=lambda item: item[0])
        sorted_tuples = dict(sorted_items)
        pages = sorted_tuples
        return pages

    def load_page(self, page: IngestPage):
        self.page = page

    def are_docs_identical(self, doc1: 'IngestLoaderDocument', doc2: 'IngestLoaderDocument') -> bool:
        return (self.are_strings_identical(doc1.page_content, doc2.page_content) and
                self.are_dicts_identical(doc1.metadata, doc2.metadata))

    def has_doc(self, doc: 'IngestLoaderDocument') -> bool:
        for document in self.cache:
            if self.are_docs_identical(document, doc):
                return True
        return False

    def add_doc(self, content: str, metadata: Dict[str, Any], collection: str, split: bool = False) -> None:
        """
        Clean the text and add a document to the appropriate collection.
        If split is True (used for the "parts" collection), only add documents
        if the content exceeds the character limit.
        """
        meta = metadata.copy()
        meta['collection'] = collection
        split_count = 7000

        cleaned_content = self.NORMALIZE_NEW_LINES(str(content))

        if not self.string_length_is_within(text=cleaned_content, max_length=split_count):
            content_parts = self.split_string_by_limit(cleaned_content, char_limit=split_count)
        else:
            content_parts = [cleaned_content]

        split_index = 0
        for part in content_parts:
            meta['split_index'] = split_index
            doc = IngestLoaderDocument(
                page_content=part,
                metadata=meta
            )
            split_index += 1
            if self.has_doc(doc):
                continue
            self.cache.append(doc)
            self.documents.append(doc)

    def run(self) -> List['IngestLoaderDocument']:
        """
        Combine the various fields from the IngestPage into six condensed documents:
         - pages: the full page content (even if very long)
         - parts: if the page content exceeds the limit, store the split parts
         - nlp: basic NLP content (only key fields)
         - agentnlp: AI agent based NLP attributes
         - images: combined image content or URLs
         - tables: combined table data
        """
        self.documents = []
        base_metadata = self.page.metadata if self.page.metadata else {}

        # --- Full page content as a single document (no splitting) ---
        Log.i("Creating full page document. -> [ pages ]")
        self.add_doc(self.page.content, base_metadata, "pages", split=False)

        # --- Combine basic NLP fields (only those useful for embeddings/similarity) ---
        try:
            if self.page.nlp:
                if self.page.nlp.combined:
                    Log.i("Creating combined basic NLP document. -> [ nlp ]")
                    self.add_doc(self.page.nlp.combined, base_metadata, "nlp", split=False)
        except Exception as e:
            Log.w(f"Error creating basic NLP document. -> [ {e} ]")
        # --- Combine FNLP fields (detailed text analytics) ---
        try:
            if self.page.fnlp:
                if self.page.fnlp.combined:
                    Log.i("Creating combined FNLP document. -> [ fnlp ]")
                    self.add_doc(self.page.fnlp.combined, base_metadata, "fnlp", split=False)
        except Exception as e:
            Log.w(f"Error creating combined NLP document: {e}")
        # --- Combine NLP Agent Fields as agentnlp ---
        try:
            agent_parts = []
            if self.page.nlp_agent:
                agent = self.page.nlp_agent
                if agent.summary:
                    agent_parts.append("Summary:\n" + agent.summary)
                if agent.paraphrase:
                    agent_parts.append("\nParaphrase:\n" + agent.paraphrase)
                if agent.sentiment:
                    agent_parts.append("\nSentiment:\n" + str(agent.sentiment))
                if agent.queries:
                    agent_parts.append("\nQueries:\n" + ", ".join(agent.queries))
                if agent.document_type:
                    agent_parts.append("\nDocument Types:\n" + ", ".join(agent.document_type))
                if agent.context_groups:
                    agent_parts.append("\nContext Groups:\n" + " ".join(str(context) for context in agent.context_groups))
            combined_agent = "\n\n".join(agent_parts)
            if combined_agent.strip():
                Log.i("Creating combined NLP Agent document. -> [ agentnlp ]")
                self.add_doc(combined_agent, base_metadata, "agentnlp", split=False)
        except Exception as e:
            Log.w(f"Error creating combined Agent NLP document: {e}")

        # --- Combine Images (byte string content or URLs) ---
        try:
            image_parts = []
            if self.page.images:
                for image in self.page.images:
                    if getattr(image, 'content', None):
                        image_parts.append(image.content)
                    elif getattr(image, 'url', None):
                        image_parts.append(image.url)
            combined_images = "\n\n".join(image_parts)
            if combined_images.strip():
                Log.i("Creating combined Images document. -> [ images ]")
                self.add_doc(combined_images, base_metadata, "images", split=False)
        except Exception as e:
            Log.w(f"Error creating Image document: {e}")

        # --- Combine Tables ---
        try:
            if self.page.tables:
                combined_tables = "\n\n".join(str(table) for table in self.page.tables)
                if combined_tables.strip():
                    Log.i("Creating combined Tables document. -> [ tables ]")
                    self.add_doc(combined_tables, base_metadata, "tables", split=False)
        except Exception as e:
            Log.w(f"Error creating Tables document: {e}")


        Log.i(f"Total condensed documents created: {len(self.documents)}")
        self.page.loader_documents = self.documents
        return self.page




if __name__ == "__main__":
    agent = IngestDocumentCreator()
    page_result = agent.execute(content=schedule_text)
    print(page_result)