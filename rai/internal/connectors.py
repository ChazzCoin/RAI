from rai.RAG.Q import Q
# from rai.internal.chromadb import ChromaClient
from rai.internal.redisdb import RaiCache
from rai.models.connectors import PostgresTables

# VECTOR_DB_CLIENT = ChromaClient()
VECTOR_DB_CLIENT = Q()
REDIS_DB_CLIENT = RaiCache()
POSTGRES_DB_CLIENT = PostgresTables