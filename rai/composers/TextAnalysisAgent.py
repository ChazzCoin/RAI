import threading
from typing import Any, List, Optional

from F import DICT, DATE, LIST

from rai.base.BaseAgents import RaiBaseAgent
from rai.base.BaseFormats import RaiContactFormat, BaseEvent, BaseLocation, UrlsModel, TextsModel
from rai.data.web.WebModels import PageExtractDetails



class TextAnalysisAgent:

    @staticmethod
    def analyze_text(content: str, **metadata) -> PageExtractDetails:
        # 1. Extract and enrich metadata
        metadata_dict = TextAnalysisAgent.metadata(content=content, **metadata)

        # 2. Extract other data
        contacts: List[RaiContactFormat] = RaiBaseAgent.pipeline("contacts", content)
        events: List[BaseEvent] = RaiBaseAgent.pipeline("events", content)
        locations: List[BaseLocation] = RaiBaseAgent.pipeline("locations", content)
        urls: List[UrlsModel] = RaiBaseAgent.pipeline("urls", content)
        context_groups: List[TextsModel] = RaiBaseAgent.pipeline("contextual_groups", content)
        summarize: List[TextsModel] = RaiBaseAgent.pipeline("summarize", content)

        # 3. Construct the final PageExtractDetails model
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

