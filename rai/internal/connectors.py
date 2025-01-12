from rai.RAG.Q import Q
# from rai.internal.chromadb import ChromaClient
from rai.internal.redisdb import RaiCache
from rai.internal.registries import RaiRegistry
from rai.models.connectors import PostgresTables

""" DATABASES """
VECTOR_DB_CLIENT = Q()
REDIS_DB_CLIENT_0 = RaiCache(db=0)
REDIS_DB_CLIENT_1 = RaiCache(db=1)
POSTGRES_DB_CLIENT = PostgresTables

""" REGISTRIES """
RAI_REGISTRY = RaiRegistry()