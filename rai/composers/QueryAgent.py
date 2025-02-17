import asyncio
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from F import DICT, LIST
from pydantic import BaseModel

from rai.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.assistant.connectors import RaiAi
from rai.base.BaseContexts import RaiBaseContexts
from rai.data.utilities.TextUtils import TextProcessor
from rai.internal.connectors import VECTOR_DB_CLIENT


QUERY_AGENT_REGISTRY = {}
def register_query_agent(name: str):
    def decorator(cls):
        QUERY_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator




class RaiQueryAgent(ABC, RaiAi, TextProcessor):
    name = None
    first = []
    second = []
    third = []
    collections = {
        "pages": 1,
        "summaries": 1,
        "context_groups": 2,
        "events": 2,
        "images": 3,
        "pdfs": 3,
        "contacts": 2,
        "locations": 2,
        "agent": 1,
        "nlp": 3
    }

    @classmethod
    async def execute_async(cls, name: str, prefix: str, query: str):
        agent_classes = QUERY_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(prefix=prefix, query=query)
    @abstractmethod
    async def run_async(self, prefix:str, query:str): pass

    def system(self, name:str): return ""
    def user(self, query:str, data:str):
        return f"""
            KNOWLEDGE LIBRARY:
            {data}
            REAL-TIME DATA:
            {self.real_time_data()}
            USER PROMPT:
            {query}
        """
    @staticmethod
    def remove_text_before_last_period(text: str) -> str:
        if '.' not in text: return text
        return text.rsplit('.', 1)[-1]
    def get_first(self, key, obj, default):
        return LIST.get(0, DICT.get(key, obj, []), default)
    def unwrap_collection(self, name:str, results: {}) -> []:
        for k,v in results.items():
            if not v: continue
            tempK = self.remove_text_before_last_period(k)
            if tempK == name:
                return results[k]


    def unwrap_results(self, results: {}) -> []:
        unwrapped_results = []
        for k,v in results.items():
            if not v: continue
            tempK = self.remove_text_before_last_period(k)
            if self.collections[tempK] == 1:
                self.first.append(v)
            elif self.collections[tempK] == 2:
                self.second.append(v)
            elif self.collections[tempK] == 3:
                self.third.append(v)
            unwrapped_results.append(v)

        flat = LIST.flatten(unwrapped_results)
        sort_flat = sorted(flat, key=lambda x: x["distance"])
        return sort_flat
    def unwrap_first(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.first:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    def unwrap_second(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.second:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    def unwrap_third(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.third:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    @staticmethod
    def unwrap_formatted(results, k=5):
        unwrapped_results = []
        count = 1
        for i in results:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])

    def filter_by_distance(self, objects: list[dict]) -> list[dict]:
        if not objects:
            return []

        # Sort the list by 'distance' in ascending order
        objects.sort(key=lambda x: x['distance'])

        # Get the top object's distance
        top_distance = objects[0]['distance']

        # Define the valid range
        min_distance = top_distance - 0.25
        max_distance = top_distance + 0.25

        # Filter objects within the valid range
        filtered_objects = [obj for obj in objects if min_distance <= obj['distance'] <= max_distance]

        return filtered_objects

    def real_time_data(self):
        now = datetime.now()
        return f"""
        Current Date & Time: {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}
        """


"""
pages = self.unwrap_collection('pages', wrapped_results)
events = self.unwrap_collection('events', wrapped_results)
top_only = self.filter_by_distance(unwrapped_results)
top_doc: RaiLoaderDocument = LIST.get(0, top_only, None)

top_doc_meta = DICT.get("metadata", top_doc, None)

top_parent_id = DICT.get("parent_id", top_doc_meta, None)
top_page_id = DICT.get("page_id", top_doc_meta, None)
top_page_number = DICT.get("page_number", top_doc_meta, None)
parent_where_query = { "parent_id": {"$eq": top_parent_id} }
page_where_query = { "page_id": {"$eq": top_page_id} }
number_where_query = { "page_number": {"$eq": top_page_number} }
where_results = VECTOR_DB_CLIENT.queryThreaded(*collection_list, user_prompt=user_prompt, k=10, where=page_where_query)

"""

class RaiQueryAgentResults(BaseModel):
    query: str
    query_expanded: str
    documents: List[dict]
    sub_documents: List[dict]

@register_query_agent("base")
class QueryAgentBaseRunner(RaiQueryAgent):
    async def run_async(self, prefix: str, query: str):
        try:
            # self.switch_engine('ollama')
            collection_list = [f"{prefix}.{c}" for c in self.collections]
            # results = await RaiBaseTextAgent.generate_async(
            #     "context_expander",
            #     user_prompt=query
            # )

            # expanded_user_prompt = DICT.get("context_expander", results, user_prompt)
            wrapped_results = VECTOR_DB_CLIENT.queryThreaded(*collection_list, user_prompt=query, k=10)
            unwrapped_results = VECTOR_DB_CLIENT.unwrap_results(wrapped_results)

            query_results = VECTOR_DB_CLIENT.unwrap_formatted(unwrapped_results, k=5)
            print(query_results)
        except Exception as e:
            print(f"Error: {e}")
            return None


async def main(prefix, query):
    # from rai.data.utilities.text_data import schedule_text
    results = await RaiQueryAgent.execute_async(
            name="base",
            prefix=prefix,
            query=query
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)


if __name__ == "__main__":
    # from rai.data.utilities.text_data import schedule_text
    q = "How do i register for placements?"
    asyncio.run(
        main(
            prefix="pcsc2025.3",
            query=q
        )
    )
    # asyncio.run(
    #     main(
    #         name="subject",
    #         user_prompt=user_prompt
    #     )
    # )