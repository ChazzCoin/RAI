import threading
from typing import Any, List, Optional

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from nlp.ext import NLPAssistant
from rai.base.BaseAgents import RaiBaseAgent
from rai.base.BaseFormats import TextsModel
from rai.data.utilities.TextUtils import to_sentences, TextProcessor
from rai.data.web.WebModels import TextNLPAgentModel, PageAnalysisModel, FNLPAssistantModel, TextImageModel, \
    DocumentAnalysisModel, NLPAssistantModel

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

    def plan_0(self):
        """
        Plan 0: Tiny content – treat as a title or small snippet.
        Minimal NLP processing is performed.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content.strip()
        # Use first 50 characters as a title
        page_model.details.title = self.cleaned_content.strip()[:50]
        # Basic NLP (tokenization, sentence splitting) is enough here.
        page_model.nlp = self.nlp(self.cleaned_content)
        return page_model

    def plan_1(self):
        """
        Plan 1: Slightly larger content – basic NLP and metadata extraction.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content
        # Use first line as title (up to 50 chars)
        page_model.details.title = self.cleaned_content.split('\n')[0][:50]
        page_model.nlp = self.nlp(self.cleaned_content)
        page_model.details.metadata = self.metadata_agent()
        return page_model

    def plan_2(self):
        """
        Plan 2: Moderate content – add an enhanced NLP agent run (e.g., summarization, sentiment).
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content
        page_model.details.title = self.cleaned_content.split('\n')[0][:50]
        page_model.nlp = self.nlp(self.cleaned_content)
        page_model.nlp_agent = self.nlp_agent()
        page_model.details.metadata = self.metadata_agent()
        return page_model

    def plan_3(self):
        """
        Plan 3: Increased content – include sentiment, document type, and morphological analysis.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content
        page_model.details.title = self.cleaned_content.split('\n')[0][:50]
        page_model.nlp = self.nlp(self.cleaned_content)
        # Run the enhanced NLP agent pipeline for summarization, sentiment, etc.
        agent_model = self.nlp_agent()
        # Perform additional morphological analysis (e.g., lemmatization)
        morpho = self.morphological_analysis(self.cleaned_content)
        meta = self.metadata_agent()
        meta.update({"morphological_analysis": morpho})
        page_model.details.metadata = meta
        page_model.nlp_agent = agent_model
        return page_model

    def plan_4(self):
        """
        Plan 4: More comprehensive analysis – add syntactic parsing, NER, and POS tagging.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content
        page_model.details.title = self.cleaned_content.split('\n')[0][:50]
        page_model.nlp = self.nlp(self.cleaned_content)
        agent_model = self.nlp_agent()
        # Additional processing: coreference resolution and POS tagging
        coref = self.coreference_resolution(self.cleaned_content)
        pos_tags = self.pos_tagging(self.cleaned_content)
        meta = self.metadata_agent()
        meta.update({"coreference": coref, "pos_tags": pos_tags})
        page_model.details.metadata = meta
        page_model.nlp_agent = agent_model
        return page_model

    def plan_5(self):
        """
        Plan 5: Extensive analysis – include summarization, paraphrasing, semantic role labeling,
        and text classification.
        """
        page_model = PageAnalysisModel()
        page_model.content = self.cleaned_content
        page_model.details.title = self.cleaned_content.split('\n')[0][:50]
        page_model.nlp = self.nlp(self.cleaned_content)
        agent_model = self.nlp_agent()
        # Additional enhancements
        srl = self.semantic_role_labeling(self.cleaned_content)
        text_class = self.text_classification(self.cleaned_content)
        meta = self.metadata_agent()
        meta.update({"semantic_role": srl, "text_classification": text_class})
        page_model.details.metadata = meta
        page_model.nlp_agent = agent_model
        return page_model

    def plan_6(self):
        """
        Plan 6: Full document analysis – for very large documents.
        Process the document in chunks and aggregate the results.
        Also perform image analysis if an image is provided.
        """
        pages = []
        original_content = self.cleaned_content
        # Process each chunk using the plan_5 pipeline (which is already very comprehensive)
        for chunk in self.split_content:
            self.cleaned_content = chunk
            chunk_page = self.plan_5()
            pages.append(chunk_page)
        self.cleaned_content = original_content  # revert to full content
        # Aggregate into a full DocumentAnalysisModel
        doc_model = DocumentAnalysisModel()
        doc_model.pages = pages
        doc_model.details.metadata = self.metadata_agent()
        # If an image was provided, add image analysis results
        if self.image:
            image_result = self.image_agent()
            if "images" not in doc_model.details.metadata:
                doc_model.details.metadata["images"] = []
            doc_model.details.metadata["images"].append(image_result)
        return doc_model

    # -------------------------------
    # NLP & Enhancement Methods
    # -------------------------------

    def fnlp(self, content: str) -> FNLPAssistantModel:
        """
        Basic NLP pipeline:
          - Tokenization (uni-grams, bi-grams, etc.)
          - Sentence and paragraph segmentation
          - Keyword extraction and URL/address detection
        """
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
        results_dict = RaiBaseAgent.pipelines(*pipeline_names, user_prompt=self.cleaned_content)
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
        """
        Merge metadata generated from the content with any provided metadata.
        """
        result = RaiBaseAgent.pipeline("metadata", self.cleaned_content).model_dump()
        meta = DICT.lazy_merge_dicts(result, self.metadata)
        return meta

    def image_agent(self) -> str:
        """
        Analyze image content via an AI pipeline.
        """
        return RaiBaseAgent.pipeline(name="image_text_extractor", image=self.image)

    # -------------------------------
    # Master methods to run the analysis
    # -------------------------------

    def analyze(self):
        """
        Run the chosen pipeline plan based on the content size.
        Returns a PageAnalysisModel or a DocumentAnalysisModel.
        """
        return self.pipeline_plan()

    def run_full_analysis(self):
        """
        For consistency, always return a DocumentAnalysisModel.
        For smaller documents, wrap the single page result in a list.
        """
        if self.content_size < 6:
            page = self.pipeline_plan()
            doc_model = DocumentAnalysisModel()
            doc_model.pages = [page]
            doc_model.details.metadata = self.metadata_agent()
            return doc_model
        else:
            return self.pipeline_plan()
