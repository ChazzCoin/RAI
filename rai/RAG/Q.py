from typing import Optional
from pydantic import BaseModel
from rai.RAG.newmain import get_all_collections
from rai.RAG.utils import query_collection
from rai.assistant.ai import RaiAi
from rai.data.extraction.RaiFileExtraction import VECTOR_DB_CLIENT
from F.LOG import Log
Log = Log("Rai Data Loader")

rai = RaiAi()

class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


def get_collections(prefix: str = None, subfix: str = None):
    try:
        # Assuming you have a ChromaDB client instance named 'VECTOR_DB_CLIENT'
        collections = VECTOR_DB_CLIENT.client.list_collections()
        collection_names = [collection.name for collection in collections]

        # Filter by prefix if provided
        if prefix:
            collection_names = [col for col in collection_names if col.startswith(prefix)]

        # Further filter by subfix if provided
        if subfix:
            filtered_collections = []
            for collection_name in collection_names:
                split_name = collection_name.split('.')
                if subfix in split_name:
                    filtered_collections.append(collection_name)
            collection_names = filtered_collections

        return collection_names

    except Exception as e:
        # Log error with proper context
        Log.e(f"Error retrieving collections from ChromaDB: {e}")
        return []

def query_chroma_form(form_data: QueryCollectionsForm, hybrid=False):
    try:
        return query_collection(
            collection_names=form_data.collection_names,
            query=form_data.query,
            embedding_function=rai.generate_embeddings,
            k=form_data.k if form_data.k else 3,
        )
    except Exception as e:
        Log.e(e)
        return {}

def query_chroma_by_prefix(prefix:str, query: str, k: int = 3, hybrid=False):
    try:
        user_collections = get_all_collections(prefix)
        Log.i(f"Collections: {user_collections}")
        return query_chroma_form(
            form_data=QueryCollectionsForm(
                collection_names=user_collections,
                query=query,
                k=k
            ),
            hybrid=hybrid
        )
    except ValueError as e:
        Log.e(f"Validation error: {e}")
        return None
    except Exception as e:
        Log.e("An unexpected error occurred", e)
        return None

if __name__ == '__main__':
    print(get_all_collections('pcsc2024', 'i'))