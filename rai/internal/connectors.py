from rai.internal.clients.redis_client import RedisDB

from rai.internal.redis_ext import RaiCache
from rai.internal.registries import RaiRegistry
from rai.internal.models.connectors import PostgresTables



""" DATABASES """
REDIS = RedisDB()


REDIS_DB_CLIENT_0 = RaiCache()
REDIS_DB_CLIENT_1 = RaiCache()
POSTGRES_DB_CLIENT = PostgresTables

""" REGISTRIES """
RAI_REGISTRY = RaiRegistry()