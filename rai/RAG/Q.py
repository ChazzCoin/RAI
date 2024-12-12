from typing import Optional

from F import LIST
from pydantic import BaseModel
from typing_extensions import Any

from rai.assistant.ai import RaiAi
from rai.assistant.openai_client import generate_embeddings
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
class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None
class ProcessDocForm(BaseModel):
    file_id: str
    collection_name: Optional[str] = None
class TextRAGForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None

def chain_collection_names(*collection_names:str):
    collection_name = ""
    index = 0
    for c in collection_names:
        if index == 0:
            collection_name = c
        else:
            collection_name = f"{collection_name}.{c}"
        index += 1
    return collection_name

def get_all_collections_by_chain(*collection_paths:str):
    try:
        # Assuming you have a ChromaDB client instance named 'VECTOR_DB_CLIENT'
        collections = VECTOR_DB_CLIENT.client.list_collections()
        collection_names = [collection.name for collection in collections]

        base_path = chain_collection_names(*collection_paths)
        # Filter by prefix if provided
        final_names = [col for col in collection_names if col.startswith(base_path)]

        return final_names

    except Exception as e:
        # Log error with proper context
        Log.e(f"Error retrieving collections from ChromaDB: {e}")
        return []

def query_chroma_by_prefix(*base_chain:str, query: str, k: int = 10, hybrid=False):
    try:
        user_collections = get_all_collections_by_chain(*base_chain)
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

def query_chroma_form(form_data: QueryCollectionsForm, hybrid=False):
    try:
        return query_collection(
            collection_names=form_data.collection_names,
            query=form_data.query,
            embedding_function=generate_embeddings,
            k=form_data.k if form_data.k else 3,
        )
    except Exception as e:
        print(e)
        return {}

def query_collection(collection_names: list[str], query: str, embedding_function, k: int) -> dict[str, list[list[Any]]]:
    results = []
    for collection_name in collection_names:
        if collection_name:
            Log.i(f"Querying [ {collection_name} ]")
            try:
                result = query_doc(
                    collection_name=collection_name,
                    query=query,
                    k=k,
                    embedding_function=embedding_function,
                )
                results.append(result.model_dump())
            except Exception as e:
                Log.e(f"Error when querying the collection: {e}")
        else:
            pass
    test = LIST.flatten(results)
    f = []
    for i in test:
        f.append(i["documents"])
    ff = LIST.flatten(f)
    return { 'documents': ff }
    # return merge_and_sort_query_results(results, k=k)

def query_doc(collection_name: str, query: str, embedding_function, k: int):
    try:
        result = VECTOR_DB_CLIENT.search(
            collection_name=collection_name,
            vectors=[embedding_function(query)],
            limit=k,
        )
        print("result", result)
        print(f"query_doc:result {result}")
        return result
    except Exception as e:
        print(e)
        raise e

def merge_and_sort_query_results(query_results: list[dict], k: int, reverse: bool = False) -> dict[str, list[list[Any]]]:
    # Initialize lists to store combined data
    combined_distances = []
    combined_documents = []
    combined_metadatas = []

    for data in query_results:
        combined_distances.extend(data["distances"][0])
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])

    # Create a list of tuples (distance, document, metadata)
    combined = list(zip(combined_distances, combined_documents, combined_metadatas))

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=reverse)

    # We don't have anything :-(
    if not combined:
        sorted_distances = []
        sorted_documents = []
        sorted_metadatas = []
    else:
        # Unzip the sorted list
        sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)

        # Slicing the lists to include only k elements
        sorted_distances = list(sorted_distances)[:k]
        sorted_documents = list(sorted_documents)[:k]
        sorted_metadatas = list(sorted_metadatas)[:k]

    # Create the output dictionary
    result = {
        "distances": [sorted_distances],
        "documents": [sorted_documents],
        "metadatas": [sorted_metadatas],
    }

    return result