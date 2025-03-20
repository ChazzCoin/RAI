import os
import redis.asyncio as ioredis
from F.LOG import Log
Log = Log("Redis Database Client")

redis_name = int(os.environ.get("REDIS_DB_NAME", 0))
redis_user = os.environ.get("REDIS_DB_USER", "rai")
redis_pass = os.environ.get("REDIS_DB_PASSWORD", None) # "local" -OR- os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "local")
redis_host = os.environ.get("REDIS_DB_HOST", "192.168.1.6")
redis_port = int(os.environ.get("REDIS_DB_PORT", 6379))


class RedisIO:

    redis_client: ioredis.Redis = None
    db = redis_name
    host = redis_host
    port = redis_port
    password = redis_pass

    def ping(self): return self.redis_client.ping()
    def is_connected(self): return self.ping()
    def get_keys_by_prefix(self, prefix): return self.keys(f"{prefix}*")
    def keys(self, query): return self.redis_client.keys(query)
    async def connect(self) -> 'RedisIO':
        """Establish a connection to the Redis server."""
        try:
            self.redis_client = ioredis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password
            )
            p = await self.redis_client.ping()  # Test connection
            print(p)
            Log.s("Successfully Connected to Remote IORedis Client.")
            return self
        except ioredis.ConnectionError as e:
            print(f"Failed to connect to Remote IORedis Client: {e}")
            return self

IORedis = RedisIO()

# loop = asyncio.new_event_loop()
# loop.run_until_complete(RedisIO.connect())
