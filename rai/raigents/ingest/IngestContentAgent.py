from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, overload

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from nlp.ext import NLPAssistant
from rai.ingest.IngestModels import IngestBrief, IngestPage, FNLPAssistantModel, NLPAssistantModel, TextNLPAgentModel
from rai.ingest.parsers.PdfDiver import RaiPdfDiver
from rai.ingest.utilities.TextUtils import TextProcessor, to_sentences
from rai.ingest.utilities.text_data import schedule_text
from rai.raigents.base.BaseImageAgents.BaseImageAgent import RaiBaseImageAgent
from rai.raigents.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent

DOC_SPLIT_SIZE = 10000

"""
 analysis
     1. Sentiment
     2. Document Type
     3. Syntactic Parsing
     4. Named Entity Recognition
     5. Part-of-Speech (POS) Tagging
     6. Relationship Extraction
     7. Topic
 enhancement
     1. RAG question generation
     2. Morphological Analysis & Lemmatization
     3. Coreference Resolution
     4. Text Classification & Categorization
     5. Semantic Role Labeling
     6. Contextual Metadata Tagging
     7. Paraphrasing & Rewriting

     ANALYZE IMAGE VIA AI
 """
DOC_SPLIT_SIZE = 30000

"""
"grammar_corrector"
language_translator
style_transfer_text

"""

class Agents:

    class Enhancement:
        class Text:
            rag_query_generator = "rag_query_generator"
            faq = "faq"
            contextual_groups = "contextual_groups"
            context_expander = "context_expander"
            text_sentiment = "text_sentiment"
            summarize = "summary"
            paraphrase = "paraphrase"
            rag = "rag"

    class Classification:
        class Text:
            objective = "objective"
            subject = "subject"
            document_type = "document_type"

        class Image:
            image_type = "image_type"

    class Extraction:
        class Text:
            metadata = "metadata"
            industry = "industry"
            form_extractor = "form_extractor"
            urls = "urls"
            events = "events"
            contacts = "contacts"
            locations = "locations"

        class Image:
            text_extractor = "text_extractor"
            table_extractor = "table_extractor"
            form_extractor = "form_extractor"

class PdfPlan:
    open = RaiPdfDiver

    def extraction(self):
        return {
            1: "rag_query_generator",
        }
    def enhancement(self):
        return {
            1: "rag_query_generator",
        }


class WebPlan:
    open = RaiPdfDiver

    def extraction(self):
        return {
            1: "rag_query_generator",
        }

    def enhancement(self):
        return {
            1: "rag_query_generator",
        }
class IngestContentAgent:
    cleaner = TextProcessor()  # Assumes a TextProcessor with a TEXT_CLEANER and content_splitter is defined

    original_content = None
    content: str = None
    metadata: dict = {}
    image = None

    content_character_count = 0
    content_size = 6
    run = None
    cleaned_content = None
    split_content = None

    ingest_brief = IngestBrief()
    ingest_pages: List[IngestPage] = []

    page = IngestPage()
    pages = {}


    # -------------------------------
    # Master methods to run the analysis
    # -------------------------------

    @classmethod
    def execute(cls, brief: IngestBrief) -> IngestPage:
        self = cls()
        self.load_brief(brief)
        return self.run()

    @classmethod
    def executes(cls, briefs: List[IngestBrief]) -> List[IngestPage]:

        def runner(brief):
            instance = cls()
            instance.load_brief(brief)
            return instance.run()

        results = {}
        with ThreadPoolExecutor() as executor:
            # Submit all briefs for processing
            future_to_index = {
                executor.submit(runner, brief): index for index, brief in enumerate(briefs)
            }
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    # Optionally, handle exceptions here.
                    results[index] = None
                    print(f"Error processing brief at index {index}: {e}")

        # Return the results in the original order.
        batched_pages = [results[i] for i in range(len(briefs))]
        return LIST.flatten(batched_pages)


    @staticmethod
    def new_page_model(content: str, page: Optional[IngestPage] = None) -> IngestPage:
        if page is None:
            page = IngestPage()
        page.details.date = DATE.get_now_month_day_year_str()  # Assumes DATE helper exists
        page.brief.original_content = content
        return page

    def load_content(self, content: str, image=None, **metadata):
        self.content = content
        self.original_content = content
        self.metadata = metadata
        self.image = image
        self.pre_process_content(content)

    def load_brief(self, brief: IngestBrief):
        self.ingest_brief = brief
        self.page.brief = brief
        self.content = self.ingest_brief.content
        self.original_content = self.ingest_brief.original_content
        self.metadata = self.ingest_brief.metadata
        self.image = self.ingest_brief.page_screenshot
        self.pre_process_content(self.ingest_brief.content)

    """Clean and split the text, then decide which plan to run."""
    def pre_process_content(self, content: str):
        self.content = self.cleaner.TEXT_CLEANER(content)
        self.content_character_count = len(content)

        # Choose a pipeline plan based on the character count
        if self.content_character_count <= 1000:
            self.content_size = 0
            self.run = self.plan_0
        elif self.content_character_count <= 5000:
            self.content_size = 1
            self.run = self.plan_1
        elif self.content_character_count <= 10000:
            self.content_size = 2
            self.run = self.plan_2
        elif self.content_character_count <= 20000:
            self.content_size = 3
            self.run = self.plan_3
        elif self.content_character_count <= 25000:
            self.content_size = 4
            self.run = self.plan_4
        elif self.content_character_count <= 30000:
            self.content_size = 5
            self.run = self.plan_5
        else:
            self.content_size = 6
            self.run = self.plan_6

        # Split content if it’s a very large document
        if self.content_character_count >= DOC_SPLIT_SIZE:
            self.split_content = self.cleaner.content_splitter.split_text(content)
        else:
            self.split_content = [content]

        self.cleaned_content = content

    # -------------------------------
    # Pipeline plans based on content size
    # -------------------------------
    def plan_0(self) -> IngestPage:
        """
            Plan 0: Tiny content – treat as a title or small snippet.
        Minimal NLP processing is performed.
        """
        page_model = IngestPage()
        page_model.content = self.cleaner.NORMALIZE_NEW_LINES(self.original_content)
        try:
            page_model.details.title = self.cleaned_content.strip()[:50]
        except:
            page_model.details.title = self.cleaned_content.strip()
        page_model.nlp = self.nlp(self.original_content)
        page_model.details.metadata = self.metadata_agent()
        return self.page_passthrough(page=page_model)
    def plan_1(self) -> IngestPage:
        return self.plan_0()
    def plan_2(self) -> IngestPage:
        page_model = self.plan_1()
        page_model.fnlp = self.fnlp(self.original_content)
        page_model.nlp_agent = self.nlp_agent()
        return self.page_passthrough(page=page_model)
    def plan_3(self) -> IngestPage:
        return self.plan_2()
    def plan_4(self) -> IngestPage:
        return self.plan_3()
    def plan_5(self) -> IngestPage:
        return self.plan_4()
    def plan_6(self) -> IngestPage:
        page_model = self.plan_5()
        # todo: run sub-documents
        return self.page_passthrough(page=page_model)

    def page_passthrough(self, page: IngestPage) -> IngestPage:
        self.page = page
        return page

    # -------------------------------
    # FairNLP/NLTK/SpaCy/AI & Enhancement Methods
    # -------------------------------

    def fnlp(self, content: str) -> FNLPAssistantModel:
        grams = nlp.Tokenizer.complete_tokenization_v2(content, toList=False)
        words = DICT.get("tokens", grams, [])
        bi_words = DICT.get("bi_grams", grams, [])
        tri_words = DICT.get("tri_grams", grams, [])
        quad_words = DICT.get("quad_grams", grams, [])

        sents = to_sentences(content)
        paras = nlp.Paragraphs.to_paragraphs(content)
        keywords = nlp.Keywords.keywords(content)

        urls = nlp.Re.extract_urls(content)
        addresses = nlp.Re.extract_addresses(content)

        nlp_model = FNLPAssistantModel()
        nlp_model.words = words
        nlp_model.bi_words = bi_words
        nlp_model.tri_words = tri_words
        nlp_model.quad_words = quad_words
        nlp_model.character_count = self.content_character_count
        nlp_model.word_count = len(words)
        nlp_model.sentence_count = len(sents)
        nlp_model.paragraph_count = len(paras)
        nlp_model.top_words = keywords
        nlp_model.addresses = addresses
        nlp_model.tags = keywords
        nlp_model.urls = urls
        return nlp_model

    def nlp(self, content: str) -> NLPAssistantModel:
        nlp_model = NLPAssistant.analyze(content)
        return nlp_model

    def nlp_agent(self) -> TextNLPAgentModel:
        """
        Enhanced NLP pipeline using parallel calls to several models:
          - Contextual grouping
          - Summarization
          - RAG query generation
          - Sentiment analysis
          - Document type detection
          - Paraphrasing
        """
        pipeline_names = [
            "contextual_groups",
            "summarize",
            "rag_query_generator",
            "text_sentiment",
            "document_type",
            "paraphrase"
        ]
        results_dict = RaiBaseTextAgent.generates(*pipeline_names, user_prompt=self.page.content)
        context_groups = LIST.remove_duplicates(results_dict["contextual_groups"])
        summarize = results_dict["summarize"]
        raq_queries = results_dict["rag_query_generator"]
        sentiment = results_dict["text_sentiment"]
        document_type = results_dict["document_type"]
        paraphrase = str(results_dict["paraphrase"])
        return TextNLPAgentModel(
            summary=summarize,
            sentiment=sentiment,
            queries=raq_queries,
            document_type=document_type,
            paraphrase=paraphrase,
            context_groups=context_groups
        )

    def metadata_agent(self):
        result = RaiBaseTextAgent.generate("metadata", self.cleaned_content).model_dump()
        meta = DICT.lazy_merge_dicts(result, self.metadata or {})
        return meta

    def image_agent(self, name) -> str:
        return RaiBaseImageAgent.generate(name=name, image=self.image)


if __name__ == "__main__":
    agent = IngestContentAgent()
    page_result = agent.execute(content=schedule_text)
    print(page_result)
