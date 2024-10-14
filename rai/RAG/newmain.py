import logging
from typing import Optional
from pydantic import BaseModel

from rai.RAG.connector import VECTOR_DB_CLIENT
from rai.RAG.utils import query_collection_with_hybrid_search, query_collection
from rai.assistant.ollama_client import generate_chroma_embeddings
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


"""

1. Who are they?
    - Are they Internal or External?
    IN: login required...
    
    EX: - not logged in...
        public.
        - who are you?
            now we simply rank/order the collections based on user type preference
        

INTERNAL:
    onboarding
internal.onboarding.coach-[file_name]
internal.onboarding.parent-[file_name]
internal.onboarding.player-[file_name]
internal.onboarding.admin-[file_name]
    development
internal.development.coach-[file_name]
internal.development.player-[file_name]
internal.development.parent-[file_name]
    schedules
internal.schedules.games-[file_name]
internal.schedules.practices-[file_name]
internal.schedules.tournaments-[file_name]
internal.schedules.events-[file_name]
    financial
internal.financial.admin-[file_name]

EXTERNAL:
    general
external.general.web-[file_name]                (guest)
external.general.faq-[file_name]                (guest)
external.general.guest-[file_name]              (guest)
external.general.parent-[file_name]
external.general.player-[file_name]
    development
external.development.guest-[file_name]          (guest)
external.development.player-[file_name]
external.development.parent-[file_name]
    schedules
external.schedules.events-[file_name]           (guest)
"""

# Define the ordered lists for each authentication type
PARENT_COLLECTIONS = ['public', 'development', 'internal']
CHILD_COLLECTIONS = ['general', 'onboarding', 'development', 'schedules', 'financial']
BABY_COLLECTIONS = ['web', 'faq', 'games', 'practices', 'events']
RaiUserToParentMap = {
    'admin': ['internal', 'external'],
    'coach': ['internal', 'external'],
    'player': ['external'],
    'parent': ['external', 'internal'],
    'guest': ['external']
}
RaiUserToChildMap = {
    'admin': ['financial', 'schedules', 'onboarding'],
    'coach': ['schedules', 'development', 'onboarding'],
    'player': ['general', 'schedules', 'development'],
    'parent': ['general', 'schedules', 'development'],
    'guest': ['general', 'development', 'schedules']
}
RaiUserToBabyMap = {
    'admin': ['admin', 'games', 'practices', 'tournaments', 'events', 'web'],
    'coach': ['games', 'practices', 'tournaments', 'events', 'guest', 'web', 'faq'],
    'player': ['web', 'faq', 'games', 'practices', 'tournaments', 'events', 'player'],
    'parent': ['web', 'faq', 'games', 'practices', 'tournaments', 'events', 'parent'],
    'guest': ['web', 'faq', 'events', 'guest']
}

COLLECTION_ROUTE = lambda parent, child, baby: f"{parent}.{child}.{baby}"
COLLECTION_ROUTE_FILE = lambda parent, child, baby, file: f"{parent}.{child}.{baby}-{file}"
COLLECTION_FILE = lambda route, file: f"{route}-{file}"


# Helper functions
def collection_route(prefix, parent, child, baby):
    return f"{prefix}.{parent}.{child}.{baby}"

def collection_route_file(prefix, parent, child, baby, file):
    return f"{prefix}.{parent}.{child}.{baby}-{file}"

def collection_file(prefix, route, file):
    return f"{prefix}.{route}-{file}"

# Validation
VALID_USER_ROLES = {'admin', 'coach', 'player', 'parent', 'guest'}

def validate_user_role(user_role):
    if user_role not in VALID_USER_ROLES:
        raise ValueError(f"Invalid user role: {user_role}")


def get_all_collections():
    try:
        # Assuming you have a ChromaDB client instance named 'chromadb_client'
        collections = VECTOR_DB_CLIENT.list_collections()
        collection_names = [collection.name for collection in collections]
        return collection_names
    except Exception as e:
        Log.e("Error retrieving collections from ChromaDB", e)
        return []


def get_user_auth_collections(prefix, user_role):
    validate_user_role(user_role)
    parent_collections = RaiUserToParentMap[user_role]
    child_collections = RaiUserToChildMap[user_role]
    baby_collections = RaiUserToBabyMap[user_role]

    # Generate route prefixes
    route_prefixes = []
    for parent in parent_collections:
        for child in child_collections:
            for baby in baby_collections:
                route_prefix = collection_route(prefix, parent, child, baby)
                route_prefixes.append(route_prefix)

    # Get all existing collection names
    all_collections = get_all_collections()

    # Filter collections that match the prefixes
    collection_names = set()
    for collection_name in all_collections:
        for prefix in route_prefixes:
            if collection_name.startswith(prefix):
                collection_names.add(collection_name)
                break  # No need to check other prefixes for this collection_name

    return list(collection_names)


# Query function
def query_chroma_by_user_auth(prefix:str, user_role: str, query: str, k: int = 50, hybrid=False):
    try:
        user_collections = get_user_auth_collections(prefix, user_role)
        Log.i(f"User '{user_role}' can access collections: {user_collections}")
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
    user_role = 'parent'
    query = 'Upcoming soccer events'
    results = query_chroma_by_user_auth(user_role, query)
    if results:
        print("Query Results:", results)
    else:
        print("No results returned.")

#     results = query_chroma_by_user_auth(user_auth="ADMIN", collection_prefix="parkcitysc", query="Who coaches the 2015 girls teams?")
#     print(results)

