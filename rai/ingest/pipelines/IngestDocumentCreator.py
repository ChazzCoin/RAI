from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from rai.assistant.AiUtils import TokenProcessor
from rai.assistant.ai_models import AiModels
from rai.ingest.utilities.IngestModels import IngestPage, IngestLoaderDocument
from rai.ingest.utilities.TextUtils import TextProcessor

from F.LOG import Log
Log = Log("composers.DocumentCreatorAgent")


class IngestDocumentCreator(TextProcessor, TokenProcessor):
    """
    A condensed document creator that processes an IngestPage and creates
    a document for each logical grouping: pages (full content), parts (split
    page content if large), nlp (basic NLP content), agentnlp (AI agent based NLP),
    images, and tables.
    """
    page = None
    cache: List['IngestLoaderDocument'] = []
    documents: List['IngestLoaderDocument'] = []

    @classmethod
    def execute(cls, page: IngestPage) -> IngestPage:
        self = cls()
        self.load_page(page)
        return self.create()

    @classmethod
    def executes(cls, pages: {}) -> {}:
        def runner(page):
            instance = cls()
            instance.load_page(page)
            return instance.create()

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

    def add_doc(self, content: str, metadata: Dict[str, Any], collection: str) -> None:
        """
        Clean the text and add a document to the appropriate collection.
        If split is True (used for the "parts" collection), only add documents
        if the content exceeds the character limit.
        """
        meta = metadata.copy()
        meta['collection'] = collection
        meta['timestamp'] = int(datetime.utcnow().timestamp())

        try:
            ai_token_count = self.count_tokens(content, AiModels.DEFAULT_OPENAI)
            meta['ai_token_count'] = int(ai_token_count)
            meta['ai_token_model'] = AiModels.DEFAULT_OPENAI
        except Exception as e:
            print(f"Error processing ai token count: {e}")
        try:
            embed_token_count = self.count_tokens(content, AiModels.DEFAULT_OPENAI_EMBEDDING)
            meta['embed_token_count'] = int(embed_token_count)
            meta['embed_token_model'] = AiModels.DEFAULT_OPENAI_EMBEDDING
        except Exception as e:
            print(f"Error processing embed token count: {e}")

        cleaned_content = self.NORMALIZE_NEW_LINES(str(content))

        doc = IngestLoaderDocument(
            page_content=cleaned_content,
            metadata=meta
        )

        if self.has_doc(doc):
            return
        self.cache.append(doc)
        self.documents.append(doc)

    def create(self) -> IngestPage:
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
        self.add_doc(self.page.content, base_metadata, "pages")

        # --- Combine basic NLP fields (only those useful for embeddings/similarity) ---
        try:
            if self.page.nlp:
                if self.page.nlp.combined:
                    Log.i("Creating combined basic NLP document. -> [ nlp ]")
                    self.add_doc(self.page.nlp.combined, base_metadata, "nlp")
        except Exception as e:
            Log.w(f"Error creating basic NLP document. -> [ {e} ]")
        # --- Combine FNLP fields (detailed text analytics) ---
        try:
            if self.page.fnlp:
                if self.page.fnlp.combined:
                    Log.i("Creating combined FNLP document. -> [ fnlp ]")
                    self.add_doc(self.page.fnlp.combined, base_metadata, "fnlp")
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
                self.add_doc(combined_agent, base_metadata, "agentnlp")
        except Exception as e:
            Log.w(f"Error creating combined Agent NLP document: {e}")

        # --- Combine Images (byte string content or URLs) ---
        try:
            image_parts = []
            if self.page.images:
                for image in self.page.images:
                    if getattr(image, 'src', None):
                        image_parts.append(image.src)
                    elif getattr(image, 'alt', None):
                        image_parts.append(image.alt)
            combined_images = "\n\n".join(image_parts)
            if combined_images.strip():
                Log.i("Creating combined Images document. -> [ images ]")
                self.add_doc(combined_images, base_metadata, "images")
        except Exception as e:
            Log.w(f"Error creating Image document: {e}")

        # --- Combine Tables ---
        try:
            if self.page.tables:
                combined_tables = "\n\n".join(str(table) for table in self.page.tables)
                if combined_tables.strip():
                    Log.i("Creating combined Tables document. -> [ tables ]")
                    self.add_doc(combined_tables, base_metadata, "tables")
        except Exception as e:
            Log.w(f"Error creating Tables document: {e}")


        Log.i(f"Total condensed documents created: {len(self.documents)}")
        self.page.loader_documents = self.documents
        return self.page
