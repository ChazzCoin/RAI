import threading
from typing import Any, List, Optional

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from rai.base.BaseAgents import RaiBaseAgent
from rai.base.BaseFormats import TextsModel
from rai.data.utilities.TextUtils import to_sentences, TextProcessor
from rai.data.web.WebModels import TextNLPAgentModel, PageAnalysisModel, TextNLPModel, TextImageModel

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
class DocumentAnalysisAgent:

    @staticmethod
    def cleaner() -> TextProcessor: return TextProcessor()

    @staticmethod
    def new_page_model(content: str, page: Optional[PageAnalysisModel]=None) -> PageAnalysisModel:
        if page is None: page = PageAnalysisModel()
        page.details.date = DATE.get_now_month_day_year_str()
        page.content = content
        return page

    @staticmethod
    def run_preprocessing(content: str) -> List[str]:
        """ 1. Clean and Split Text """
        cleaner = DocumentAnalysisAgent.cleaner()
        content = cleaner.TEXT_CLEANER(content)
        char_count = len(content)

        if char_count >= DOC_SPLIT_SIZE:
            split_content = cleaner.content_splitter.split_text(content)
        else:
            split_content = [content]

        return split_content

    @staticmethod
    def nlp(content: str) -> TextNLPModel:

        char_count = len(content)

        grams: {} = nlp.Tokenizer.complete_tokenization_v2(content, toList=False)
        words = DICT.get("tokens", grams, [])
        bi_words = DICT.get("bi_grams", grams, [])
        tri_words = DICT.get("tri_grams", grams, [])
        quad_words = DICT.get("quad_grams", grams, [])

        sents = to_sentences(content)
        paras = nlp.Paragraphs.to_paragraphs(content)
        keywords = nlp.Keywords.keywords(content)

        urls = nlp.Re.extract_urls(content)
        addresses = nlp.Re.extract_addresses(content)

        word_count = len(words)
        sent_count = len(sents)
        paras_count = len(paras)

        nlp_model = TextNLPModel()
        nlp_model.words = words
        nlp_model.bi_words = bi_words
        nlp_model.tri_words = tri_words
        nlp_model.quad_words = quad_words
        nlp_model.character_count = char_count
        nlp_model.word_count = word_count
        nlp_model.sentence_count = sent_count
        nlp_model.paragraph_count = paras_count
        nlp_model.top_words = keywords
        nlp_model.addresses = addresses
        nlp_model.tags = keywords
        nlp_model.urls = urls
        return nlp_model

    @staticmethod
    def image_agent(image) -> str:
        return RaiBaseAgent.pipeline(name="image_text_extractor", image=image)

    @staticmethod
    def nlp_agent(content: str) -> TextNLPAgentModel:
        # ------------------
        # PARALLEL PIPELINE CALLS
        # ------------------
        pipeline_names = [
            "contextual_groups",
            "summarize",
            "rag_query_generator",
            "text_sentiment",
            "document_type",
            "paraphrase"
        ]
        results_dict = RaiBaseAgent.pipelines(*pipeline_names, user_prompt=content, image=image)
        context_groups: List[TextsModel] = LIST.remove_duplicates(results_dict["contextual_groups"])
        summarize: str = results_dict["summarize"]
        raq_queries: list = results_dict["rag_query_generator"]
        sentiment: list = results_dict["text_sentiment"]
        document_type: list = results_dict["document_type"]
        paraphrase: str = str(results_dict["paraphrase"])
        # ------------------
        # CONSTRUCT THE FINAL MODEL
        # ------------------
        return TextNLPAgentModel(
            summary=summarize,
            sentiment=sentiment,
            queries=raq_queries,
            document_type=document_type,
            paraphrase=paraphrase,
            context_groups=context_groups
        )


    @staticmethod
    def metadata(content:str, **metadata):
        result = RaiBaseAgent.pipeline("metadata", content).model_dump()
        meta = DICT.lazy_merge_dicts(result, metadata)
        return meta

