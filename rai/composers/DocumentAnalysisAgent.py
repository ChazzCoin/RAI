from typing import Optional

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from nlp.ext import NLPAssistant
from rai.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.data.utilities.TextUtils import to_sentences, TextProcessor
from rai.data.web.WebModels import TextNLPAgentModel, PageAnalysisModel, FNLPAssistantModel, NLPAssistantModel

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
DOC_SPLIT_SIZE = 10000

class DocumentAnalysisAgent(NLPAssistant):
    cleaner = TextProcessor()  # Assumes a TextProcessor with a TEXT_CLEANER and content_splitter is defined

    content: str = None
    metadata: dict = {}
    image = None

    content_character_count = 0
    content_size = 6
    pipeline_plan = None
    cleaned_content = None
    split_content = None

    def __init__(self, content: str, image=None, **metadata):
        super().__init__(content)
        self.content = content
        self.metadata = metadata
        self.image = image
        self.pre_process_content(content)

    @staticmethod
    def new_page_model(content: str, page: Optional[PageAnalysisModel] = None) -> PageAnalysisModel:
        if page is None:
            page = PageAnalysisModel()
        page.details.date = DATE.get_now_month_day_year_str()  # Assumes DATE helper exists
        page.content = content
        return page

    def pre_process_content(self, content: str):
        """Clean and split the text, then decide which plan to run."""
        content = self.cleaner.TEXT_CLEANER(content)
        self.content_character_count = len(content)

        # Choose a pipeline plan based on the character count
        if self.content_character_count <= 250:
            self.content_size = 0
            self.pipeline_plan = self.plan_0
        elif self.content_character_count <= 500:
            self.content_size = 1
            self.pipeline_plan = self.plan_1
        elif self.content_character_count <= 1000:
            self.content_size = 2
            self.pipeline_plan = self.plan_2
        elif self.content_character_count <= 1500:
            self.content_size = 3
            self.pipeline_plan = self.plan_3
        elif self.content_character_count <= 5000:
            self.content_size = 4
            self.pipeline_plan = self.plan_4
        elif self.content_character_count <= 10000:
            self.content_size = 5
            self.pipeline_plan = self.plan_5
        else:
            self.content_size = 6
            self.pipeline_plan = self.plan_6

        # Split content if it’s a very large document
        if self.content_character_count >= DOC_SPLIT_SIZE:
            self.split_content = self.cleaner.content_splitter.split_text(content)
        else:
            self.split_content = [content]

        self.cleaned_content = content

    # -------------------------------
    # Pipeline plans based on content size
    # -------------------------------

    def plan_0(self) -> PageAnalysisModel:
        """
            Plan 0: Tiny content – treat as a title or small snippet.
        Minimal NLP processing is performed.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content.strip()
        try:
            page_model.details.title = self.cleaned_content.strip()[:50]
        except:
            page_model.details.title = self.cleaned_content.strip()
        page_model.nlp = self.nlp(self.cleaned_content)
        page_model.details.metadata = self.metadata_agent()
        return page_model

    def plan_1(self) -> PageAnalysisModel:
        return self.plan_0()

    def plan_2(self) -> PageAnalysisModel:
        page_model = self.plan_1()
        page_model.fnlp = self.fnlp(self.cleaned_content)
        page_model.nlp_agent = self.nlp_agent()
        return page_model

    def plan_3(self) -> PageAnalysisModel:
        return self.plan_2()

    def plan_4(self) -> PageAnalysisModel:
        return self.plan_3()

    def plan_5(self) -> PageAnalysisModel:
        return self.plan_4()

    def plan_6(self) -> PageAnalysisModel:
        page_model = self.plan_5()
        # todo: run sub-documents
        return page_model

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
        return self.pipeline(content)

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
        results_dict = RaiBaseTextAgent.generates(*pipeline_names, user_prompt=self.cleaned_content)
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
        meta = DICT.lazy_merge_dicts(result, self.metadata)
        return meta

    def image_agent(self) -> str:
        return RaiBaseTextAgent.generate(name="image_text_extractor", image=self.image)

    # -------------------------------
    # Master methods to run the analysis
    # -------------------------------

    def analyze(self):
        return self.pipeline_plan()

