import json
from abc import abstractmethod, ABC
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from nlp.ext import NLPAssistant
from rai.agentic.ai_tools.image_tools.r_tools import rImageTools
from rai.ingest.utilities.IngestModels import IngestBrief, IngestPage, FNLPAssistantModel, NLPAssistantModel, TextNLPAgentModel
from rai.ingest.utilities.TextUtils import TextProcessor, to_sentences
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools

INGEST_NLP_AGENT_REGISTRY = {}

def register_ingest_nlp_agent_plan(name: str):
    def decorator(cls):
        INGEST_NLP_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


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




class IngestNLPAgent(ABC):
    name = "base"
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
    def get_registry(cls): return INGEST_NLP_AGENT_REGISTRY

    @classmethod
    def execute(cls, name:str, brief: IngestBrief) -> IngestPage:
        name = name.split("-", 1)[0]
        agent_cls = INGEST_NLP_AGENT_REGISTRY.get(name)
        cls.name = name
        self = agent_cls[0]()
        self.load_brief(brief)
        return self.plan()

    @classmethod
    def executes(cls, name:str, briefs: {}) -> {}:
        name = name.split("-", 1)[0]
        def runner(brief):
            agent_cls = INGEST_NLP_AGENT_REGISTRY.get(name)
            cls.name = name
            instance = agent_cls[0]()
            instance.load_brief(brief)
            return instance.plan()

        results = {}
        with ThreadPoolExecutor() as executor:
            # Submit all briefs for processing
            future_to_index = {
                executor.submit(runner, brief): index for index, brief in enumerate(briefs.values())
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
        sorted_items = sorted(results.items(), key=lambda item: item[0])
        sorted_tuples = dict(sorted_items)
        pages = sorted_tuples
        return pages

    @abstractmethod
    def plan(self) -> IngestPage:
        pass

    def initialize(self):
        self.page = IngestPage()

    def load_content(self, content: str, image=None, **metadata):
        self.initialize()
        self.content = content
        self.original_content = content
        self.metadata = metadata
        self.image = image
        self.pre_process_content(content)

    def load_brief(self, brief: IngestBrief):
        self.initialize()
        self.ingest_brief = brief
        self.page.brief = brief
        self.content = self.ingest_brief.content
        self.original_content = self.ingest_brief.content
        self.metadata = self.ingest_brief.metadata
        self.image = self.ingest_brief.page_screenshot
        self.pre_process_content(self.ingest_brief.content)

    """Clean and split the text, then decide which plan to run."""
    def pre_process_content(self, content: str):
        self.content = self.cleaner.NORMALIZER(content)
        self.content_character_count = len(content)
        self.cleaned_content = content
        self.page.content = self.cleaner.NORMALIZER(self.original_content)
        self.setup_metadata()
    # -------------------------------
    # Pipeline plans based on content size
    # -------------------------------
    def plan_nlp_basic(self) -> IngestPage:
        print("INGEST: Starting Plan NLP Basic")
        self.nlp(self.original_content)
        self.metadata_nlp()
        self.fnlp(self.original_content)
        self.metadata_fnlp()
        return self.page
    def plan_nlp_agent(self) -> IngestPage:
        print("INGEST: Starting Plan NLP Agent")
        self.nlp_agent()
        self.metadata_agent()
        return self.page

    # -------------------------------
    # FairNLP/NLTK/SpaCy/AI & Enhancement Methods
    # -------------------------------
    def fnlp(self, content: str) -> IngestPage:
        try:
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

            self.page.fnlp = FNLPAssistantModel()
            self.page.fnlp.words = words
            self.page.fnlp.bi_words = bi_words
            self.page.fnlp.tri_words = tri_words
            self.page.fnlp.quad_words = quad_words
            self.page.fnlp.character_count = self.content_character_count
            self.page.fnlp.word_count = len(words)
            self.page.fnlp.sentence_count = len(sents)
            self.page.fnlp.paragraph_count = len(paras)
            self.page.fnlp.top_words = keywords
            self.page.fnlp.addresses = addresses
            self.page.fnlp.tags = keywords
            self.page.fnlp.urls = urls
            self.page.fnlp.combined = self.combine_fnlp()
            return self.page
        except Exception as e:
            print(e)
            return self.page
    def nlp(self, content: str) -> NLPAssistantModel:
        self.page.nlp = NLPAssistant.analyze(content)
        self.page.nlp.combined = self.combine_nlp()
        return self.page.nlp
    def nlp_agent(self) -> IngestPage:
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
        try:
            results_dict = rTextTools.tools(*pipeline_names, user_prompt=self.page.content)
            context_groups = LIST.remove_duplicates(results_dict["contextual_groups"])
            summarize = results_dict["summarize"]
            raq_queries = results_dict["rag_query_generator"]
            sentiment = results_dict["text_sentiment"]
            document_type = results_dict["document_type"]
            paraphrase = str(results_dict["paraphrase"])
            self.page.nlp_agent = TextNLPAgentModel(
                summary=summarize,
                sentiment=sentiment,
                queries=raq_queries,
                document_type=document_type,
                paraphrase=paraphrase,
                context_groups=context_groups
            )
            return self.page
        except Exception as e:
            print(e)
            return self.page
    def combine_fnlp(self) -> str:
        fnlp_parts = []
        try:
            if self.page.fnlp:
                if hasattr(self.page.fnlp, 'character_count'):
                    fnlp_parts.append("\nCharacter Count:\n" + str(self.page.fnlp.character_count))
                if hasattr(self.page.fnlp, 'word_count'):
                    fnlp_parts.append("\nWord Count:\n" + str(self.page.fnlp.word_count))
                if hasattr(self.page.fnlp, 'sentence_count'):
                    fnlp_parts.append("\nSentence Count:\n" + str(self.page.fnlp.sentence_count))
                if hasattr(self.page.fnlp, 'paragraph_count'):
                    fnlp_parts.append("\nParagraph Count:\n" + str(self.page.fnlp.paragraph_count))
                if hasattr(self.page.fnlp, 'top_words') and self.page.fnlp.top_words:
                    fnlp_parts.append("\nTop Words:\n" + ", ".join(self.page.fnlp.top_words))
                if hasattr(self.page.fnlp, 'words') and self.page.fnlp.words:
                    fnlp_parts.append("\nWords:\n" + "\n - ".join(self.page.fnlp.words))
                if hasattr(self.page.fnlp, 'addresses') and self.page.fnlp.addresses:
                    fnlp_parts.append("\nAddresses:\n" + ", ".join(self.page.fnlp.addresses))
                if hasattr(self.page.fnlp, 'tags') and self.page.fnlp.tags:
                    fnlp_parts.append("Tags:\n" + ", ".join(self.page.fnlp.tags))
                if hasattr(self.page.fnlp, 'urls') and self.page.fnlp.urls:
                    fnlp_parts.append("\nURLs:\n" + ", ".join(self.page.fnlp.urls))
                return "\n\n".join(fnlp_parts)
        except Exception as e:
            print(e)
        return ""
    def combine_nlp(self) -> str:
        nlp_parts = []
        try:
            if self.page.nlp:
                if self.page.nlp.summary:
                    nlp_parts.append("Summary:\n" + json.dumps(self.page.nlp.summary))
                if self.page.nlp.sentences:
                    nlp_parts.append("\nSentences:\n" + " ".join(self.page.nlp.sentences))
                if self.page.nlp.paragraphs:
                    nlp_parts.append("\nParagraphs:\n" + "\n".join(self.page.nlp.paragraphs))
                if self.page.nlp.lemmas:
                    nlp_parts.append("\nLemmas:\n" + " ".join(self.page.nlp.lemmas))
                if self.page.nlp.sentiment:
                    nlp_parts.append("\nSentiment:\n" + str(self.page.nlp.sentiment))
                if self.page.nlp.named_entities:
                    nlp_parts.append("\nNamed Entities:\n" + str(self.page.nlp.named_entities))
                if self.page.nlp.frequency_distribution:
                    nlp_parts.append("\nFrequency Distribution:\n" + str(self.page.nlp.frequency_distribution))
                if self.page.nlp.urls:
                    nlp_parts.append("\nUrls:\n" + str(self.page.nlp.urls))
                return "\n\n".join(nlp_parts)
        except Exception as e:
            print(e)
        return ""
    def metadata_agent(self):
        try:
            result = rTextTools.tool("metadata", self.cleaned_content + self.combine_nlp())
            self.metadata = DICT.lazy_merge_dicts(result, self.metadata or {})
            self.page.metadata = self.metadata
            return self.metadata
        except Exception as e:
            print(e)
            return self.metadata
    def setup_metadata(self) -> Dict[str, Any]:

        if not self.metadata: self.metadata = {}
        elif type(self.metadata) is not dict: self.metadata = {}

        self.metadata["date_created"] = DATE.get_now_month_day_year_str()

        self.metadata["record_id"] = str(self.page.record_id)
        self.metadata["page_id"] = str(self.page.id)
        try: self.metadata["brief_id"] = str(self.page.brief.id)
        except: pass
        try: self.metadata["page_index"] = str(self.page.brief.index)
        except: pass
        try: self.metadata["title"] = self.cleaned_content.strip()[:50]
        except: self.metadata["title"] = self.cleaned_content.strip()
        try: self.metadata["page_screenshot"] = str(self.page.brief.page_screenshot)
        except: pass
        self.page.metadata = self.metadata
        return self.metadata
    def metadata_nlp(self) -> Dict[str, Any]:
        # Process basic NLP fields.
        try:
            if self.page.nlp:
                if self.page.nlp.summary:
                    self.metadata["summary"] = json.dumps(self.page.nlp.summary)
                if self.page.nlp.lemmas:
                    self.metadata["lemmas"] = " ".join(self.page.nlp.lemmas)
                if self.page.nlp.sentiment:
                    self.metadata["sentiment"] = str(self.page.nlp.sentiment)
                if self.page.nlp.named_entities:
                    self.metadata["named_entities"] = str(self.page.nlp.named_entities)
                if self.page.nlp.frequency_distribution:
                    self.metadata["frequency_distribution"] = str(self.page.nlp.frequency_distribution)
                if self.page.nlp.urls:
                    self.metadata["n_urls"] = str(self.page.nlp.urls)
            self.page.metadata = self.metadata
            return self.metadata
        except Exception as e:
            print(e)
            return self.metadata
    def metadata_fnlp(self) -> Dict[str, Any]:
        # Process detailed FNLP fields.
        try:
            if self.page.fnlp:
                if hasattr(self.page.fnlp, 'character_count'):
                    self.metadata["character_count"] = str(self.page.fnlp.character_count)
                if hasattr(self.page.fnlp, 'word_count'):
                    self.metadata["word_count"] = str(self.page.fnlp.word_count)
                if hasattr(self.page.fnlp, 'sentence_count'):
                    self.metadata["sentence_count"] = str(self.page.fnlp.sentence_count)
                if hasattr(self.page.fnlp, 'paragraph_count'):
                    self.metadata["paragraph_count"] = str(self.page.fnlp.paragraph_count)
                if hasattr(self.page.fnlp, 'top_words') and self.page.fnlp.top_words:
                    self.metadata["top_words"] = ", ".join(self.page.fnlp.top_words)
                if hasattr(self.page.fnlp, 'words') and self.page.fnlp.words:
                    self.metadata["words"] = "\n - ".join(self.page.fnlp.words)
                if hasattr(self.page.fnlp, 'addresses') and self.page.fnlp.addresses:
                    self.metadata["addresses"] = ", ".join(self.page.fnlp.addresses)
                if hasattr(self.page.fnlp, 'tags') and self.page.fnlp.tags:
                    self.metadata["tags"] = ", ".join(self.page.fnlp.tags)
                if hasattr(self.page.fnlp, 'urls') and self.page.fnlp.urls:
                    self.metadata["f_urls"] = ", ".join(self.page.fnlp.urls)

            self.page.metadata = self.metadata
            return self.metadata
        except Exception as e:
            print(e)
            return self.metadata
    def image_agent(self, name) -> Optional[str]:
        try:
            return rImageTools.tool(name=name, image=self.image)
        except Exception as e:
            print(e)
            return None

@register_ingest_nlp_agent_plan("injection")
class IngestNLPAgentInjection(IngestNLPAgent):
    def plan(self) -> IngestPage:
        print("INGEST: Starting Plan [ Injection ]")
        return self.page

@register_ingest_nlp_agent_plan("store")
class IngestNLPAgentStore(IngestNLPAgent):
    def plan(self) -> IngestPage:
        print("INGEST: Starting Plan [ Store ]")
        return self.plan_nlp_basic()

@register_ingest_nlp_agent_plan("deep")
class IngestNLPAgentInjection(IngestNLPAgent):
    def plan(self) -> IngestPage:
        print("INGEST: Starting Plan [ Deep ]")
        # Basic NLP
        self.nlp(self.original_content)
        self.metadata_nlp()
        # Fair NLP
        self.fnlp(self.original_content)
        self.metadata_fnlp()
        # NLP Agent
        self.nlp_agent()
        self.metadata_agent()
        return self.page
