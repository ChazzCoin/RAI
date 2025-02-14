import threading
from typing import Any, List, Optional

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from rai.base.BaseAgents import RaiBaseAgent
from rai.base.BaseFormats import RaiContactFormat, BaseEvent, BaseLocation, UrlsModel, TextsModel
from rai.data.utilities.TextUtils import to_sentences
from rai.data.web.WebModels import PageExtractDetails



class TextAnalysisAgent:

    @staticmethod
    def analyze_text_async(content: str, **metadata) -> PageExtractDetails:
        """
        1. Extract and enrich metadata
        2. Run pipelines in parallel (contacts, events, locations, urls, context_groups, summarize)
        3. Construct and return final PageExtractDetails
        """
        # ------------------
        # 1. METADATA ENRICHMENT
        # ------------------
        metadata_dict = TextAnalysisAgent.metadata(content=content, **metadata)

        # ------------------
        # 2. PARALLEL PIPELINE CALLS
        # ------------------
        pipeline_names = [
            "contextual_groups",
            "summarize",
            "rag_query_generator",
            "text_sentiment",
            "document_type",
            "paraphrase"
        ]

        # Shared dictionary to store results keyed by pipeline name
        results_dict = {}

        # Worker function to call the pipeline in a thread
        def call_pipeline(name: str, text: str, store: dict):
            store[name] = RaiBaseAgent.pipeline(name, text)

        # Create and start a thread for each pipeline call
        threads = []
        for name in pipeline_names:
            thread = threading.Thread(
                target=call_pipeline,
                args=(name, content, results_dict)
            )
            threads.append(thread)
            thread.start()

        # Join all threads to ensure they complete
        for t in threads:
            t.join()

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
        char_count = len(content)
        split_count = 0
        if char_count >= 10000: split_count = 2
        elif char_count >= 5000: split_count = 1

        # Retrieve parallel results
        context_groups: List[TextsModel] = LIST.remove_duplicates(results_dict["contextual_groups"])
        summarize: str = results_dict["summarize"]

        raq_queries: list = results_dict["rag_query_generator"]
        sentiment: list = results_dict["text_sentiment"]
        document_type: list = results_dict["document_type"]
        paraphrase: str = str(results_dict["paraphrase"])

        grams: {} = nlp.Tokenizer.complete_tokenization_v2(content)
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

        # ------------------
        # 3. CONSTRUCT THE FINAL MODEL
        # ------------------
        page_details = PageExtractDetails(

            date=DATE.get_now_month_day_year_str(),

            content=content,
            summary=summarize,
            sentences=sents,
            paragraphs=paras,

            sentiment=sentiment,
            queries=raq_queries,
            document_type=document_type,
            paraphrase=paraphrase,

            words=words,
            bi_words=bi_words,
            tri_words=tri_words,
            quad_words=quad_words,

            character_count=char_count,
            word_count=word_count,
            sentence_count=sent_count,
            paragraph_count=paras_count,
            top_words=keywords,

            urls=urls,
            tags=keywords,
            contacts=[],
            locations=[],
            addresses=addresses,
            events=[],
            context_groups=context_groups,

            metadata=metadata_dict
        )

        return page_details

    @staticmethod
    def analyze_deep_text_async(content: str, **metadata) -> PageExtractDetails:
        """
        1. Extract and enrich metadata
        2. Run pipelines in parallel (contacts, events, locations, urls, context_groups, summarize)
        3. Construct and return final PageExtractDetails
        """
        # ------------------
        # 1. METADATA ENRICHMENT
        # ------------------
        metadata_dict = TextAnalysisAgent.metadata(content=content, **metadata)

        # ------------------
        # 2. PARALLEL PIPELINE CALLS
        # ------------------
        pipeline_names = [
            "contacts",
            "events",
            "locations",
            "urls",
            "contextual_groups",
            "summarize"
        ]

        # Shared dictionary to store results keyed by pipeline name
        results_dict = {}

        # Worker function to call the pipeline in a thread
        def call_pipeline(name: str, text: str, store: dict):
            store[name] = RaiBaseAgent.pipeline(name, text)

        # Create and start a thread for each pipeline call
        threads = []
        for name in pipeline_names:
            thread = threading.Thread(
                target=call_pipeline,
                args=(name, content, results_dict)
            )
            threads.append(thread)
            thread.start()

        # Join all threads to ensure they complete
        for t in threads:
            t.join()

        # Retrieve parallel results
        contacts: List[RaiContactFormat] = LIST.remove_duplicates(results_dict["contacts"])
        events: List[BaseEvent] = LIST.remove_duplicates(results_dict["events"])
        if type(events) in [list]:
            first = LIST.get(0, events, None)
            if first is None:
                events = []
            elif type(first) not in [BaseEvent]:
                events = []
        else:
            events = []
        locations: List[BaseLocation] = LIST.remove_duplicates(results_dict["locations"])
        urls: List[UrlsModel] = LIST.remove_duplicates(results_dict["urls"])
        context_groups: List[TextsModel] = LIST.remove_duplicates(results_dict["contextual_groups"])
        summarize: str = results_dict["summarize"]

        # ------------------
        # 3. CONSTRUCT THE FINAL MODEL
        # ------------------
        page_details = PageExtractDetails(
            date=DATE.get_now_month_day_year_str(),
            content=content,
            summary=summarize,
            urls=urls,
            tags=DICT.get_any(keys=("tags", "keywords"), dic=metadata_dict, default=[]),
            contacts=contacts,
            locations=locations,
            events=events,
            context_groups=context_groups,
            metadata=metadata_dict
        )

        return page_details

    @staticmethod
    def metadata(content:str, **metadata):
        result = RaiBaseAgent.pipeline("metadata", content).model_dump()
        meta = DICT.lazy_merge_dicts(result, metadata)
        return meta

