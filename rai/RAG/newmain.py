import enum
import logging
from typing import Optional
from pydantic import BaseModel
from assistant.ollama_client import generate_chroma_embeddings
from rai.RAG.utils import query_collection_with_hybrid_search, query_collection
from rai.env import SRC_LOG_LEVELS
from rai import app

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])
from F.LOG import Log
Log = Log("Rai Data Loader")

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


# Define the ordered lists for each authentication type
RaiUserType = {
    'ADMIN': ['internal', 'development', 'main'],
    'COACH': ['development', 'internal', 'main'],
    'PLAYER': ['development', 'main'],
    'PARENT': ['main', 'development'],
    'GUEST': ['main']
}

# Example usage
# Assume you have a function to determine the user's auth type
def get_user_auth_collections(auth_type:str):
   return RaiUserType.get(auth_type, [])

def query_chroma_by_user_auth(user_auth:str, collection_prefix:str, query:str, k:int=50, hybrid=False):

    user_collections = get_user_auth_collections(user_auth)
    collections = []
    for suffix in user_collections:
        collections.append(f"{collection_prefix}-{suffix}")
    return query_chroma_form(
        form_data=QueryCollectionsForm(
            collection_names=collections,
            query=query, k=k
        ), hybrid=hybrid
    )

def query_chroma(*collections:str, query:str, k:int=10, hybrid=False):
    return query_chroma_form(
        form_data=QueryCollectionsForm(
            collection_names=collections,
            query=query, k=k
        ), hybrid=hybrid
    )

def query_chroma_form(form_data: QueryCollectionsForm, hybrid=False):
    try:
        if hybrid:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_chroma_embeddings,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function="",
                r=(
                    form_data.r if form_data.r else 0.0
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=generate_chroma_embeddings,
                k=form_data.k if form_data.k else 3,
            )

    except Exception as e:
        log.exception(e)
        return {}

if __name__ == "__main__":
    results = query_chroma_by_user_auth(user_auth="ADMIN", collection_prefix="parkcitysc", query="Who coaches the 2015 girls teams?")
    print(results)

