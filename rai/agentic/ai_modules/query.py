from collections import defaultdict
from datetime import datetime, timedelta
from typing import Union, Dict, List, Any


class QueryModule:
    @staticmethod
    def parse_date_query(date_query: str) -> datetime:
        qd = datetime.strptime(date_query, "%Y-%m-%d")
        return datetime(qd.year, qd.month, qd.day)
    @staticmethod
    def where_id_equals(idx: str):
        return QueryModule.where_key_equals(key='id', value=idx)
    @staticmethod
    def where_key_equals(key, value):
        return {key: {"$eq": value}}
    @staticmethod
    def where_key_is_gte(key, value):
        return {key: {"$gte": value}}
    @staticmethod
    def where_key_is_lte(key, value):
        return {key: {"$lte": value}}
    @staticmethod
    def _get_date(query_date: Union[str, datetime]):
        if isinstance(query_date, str):
            query_date = datetime.strptime(query_date, "%Y-%m-%d")
        return datetime(query_date.year, query_date.month, query_date.day)
    @staticmethod
    def _get_date_now():
        return int(datetime.now().timestamp())
    @staticmethod
    def _get_date_tomorrow():
        return int((datetime.now() + timedelta(days=1)).timestamp())
    @staticmethod
    def _get_date_yesterday():
        return int((datetime.now() - timedelta(days=1)).timestamp())
    @staticmethod
    def _get_date_x_days_in_future(x: int):
        return int((datetime.now() + timedelta(days=x)).timestamp())
    @staticmethod
    def _get_date_x_days_ago(x: int):
        return int((datetime.now() - timedelta(days=x)).timestamp())
    @staticmethod
    def where_is_today():
        return {"$and": [{"timestamp": {"$gte": QueryModule._get_date_now()}},
                         {"timestamp": {"$lt": QueryModule._get_date_tomorrow()}}]}
    @staticmethod
    def where_between_dates(start: datetime, end: datetime):
        return {"$and": [{"timestamp": {"$gte": start}}, {"timestamp": {"$lt": end}}]}
    @staticmethod
    def where_parent_id(parent_id):
        return {"parent_id": {"$eq": parent_id}}
    @staticmethod
    def where_page_id(page_id):
        return {"page_id": {"$eq": page_id}}
    @staticmethod
    def where_page_number(page_number):
        return {"page_number": {"$eq": page_number}}
    @staticmethod
    def remove_text_before_last_period(text: str) -> str:
        if '.' not in text: return text
        return text.rsplit('.', 1)[-1]
    @staticmethod
    def filter_by_distance(objects: list[dict]) -> list[dict]:
        if not objects: return []
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
    @staticmethod
    def real_time_data():
        now = datetime.now()
        return f""" Current Date & Time: {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")} """
    @staticmethod
    def sort_documents(documents: List[Dict[str, Any]]) -> Dict[str, Dict[int, Dict[str, Any]]]:
        sorted_by_brief = defaultdict(list)
        # Group documents by brief_id
        for doc in documents:
            brief_id = doc['metadata']['brief_id']
            sorted_by_brief[brief_id].append(doc)
        # Sort each brief_id group by page_index
        result = {}
        for brief_id, docs in sorted_by_brief.items():
            sorted_docs = sorted(docs, key=lambda d: d['metadata']['page_index'])
            # Map sorted docs by page_index
            result[brief_id] = {doc['metadata']['page_index']: doc for doc in sorted_docs}
        return result

