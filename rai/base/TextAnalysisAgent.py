from typing import Any, List, Optional

from F import DICT, DATE

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
    def metadata(content:str, **metadata):
        result = RaiBaseAgent.pipeline("metadata", content).model_dump()
        meta = DICT.lazy_merge_dicts(result, metadata)
        return meta

