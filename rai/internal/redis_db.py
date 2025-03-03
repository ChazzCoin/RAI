from typing import overload
import redis, json, os
from torch.cuda.nccl import unique_id

from F.LOG import Log
Log = Log("Redis Database Client")

redis_name = int(os.environ.get("REDIS_DB_NAME", 0))
redis_user = os.environ.get("REDIS_DB_USER", "rai")
redis_pass = os.environ.get("REDIS_DB_PASSWORD", None) # "local" -OR- os.environ.get("DEFAULT_CHROMA_SERVER_HOST", "local")
redis_host = os.environ.get("REDIS_DB_HOST", "192.168.1.6")
redis_port = int(os.environ.get("REDIS_DB_PORT", 6379))

class RedisClient:
    redis_client: redis.client = None

    def __init__(self, db:int=redis_name):
        """
        Initialize the Redis client.
        :param host: Redis server hostname (default: 'localhost')
        :param port: Redis server port (default: 6379)
        :param db: Redis database index (default: 0)
        :param password: Password for Redis server (default: None)
        """
        try:
            self.host = redis_host
            self.port = redis_port
            self.db = db
            self.password = redis_pass
            self.connect()
        except Exception as e:
            Log.e(e)

    def ping(self):
        return self.redis_client.ping()

    def is_connected(self):
        return self.ping()

    def get_keys_by_prefix(self, prefix):
        return self.keys(f"{prefix}*")

    def keys(self, query):
        return self.redis_client.keys(query)

    def connect(self):
        """Establish a connection to the Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password
            )
            p = self.redis_client.ping()  # Test connection
            print(p)
            Log.s("Successfully Connected to Remote Redis Client.")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Remote Redis Client: {e}")

    def set_key(self, key, value, ttl=None):
        """
        Set a key-value pair in Redis with an optional TTL.

        :param key: The key to set.
        :param value: The value to set (will be serialized to JSON).
        :param ttl: Time to Live in seconds (optional).
        """
        try:
            serialized_value = json.dumps(value) if type(value) in [dict] else str(value)
            if ttl:
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                self.redis_client.set(key, serialized_value)
            print(f"Key '{key}' set successfully.")
        except Exception as e:
            print(f"Failed to set key '{key}': {e}")

    def get_key(self, key, default=None):
        """
        Retrieve a value by key from Redis.

        :param key: The key to retrieve.
        :return: The value associated with the key (deserialized from JSON).
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                try:
                    return json.loads(value)
                except Exception as e:
                    Log.e(e)
                    return value.decode("utf-8")
            else:
                print(f"Key '{key}' does not exist.")
                return None
        except Exception as e:
            print(f"Failed to get key '{key}': {e}")
            return default

    def delete_key(self, key):
        """
        Delete a key from Redis.

        :param key: The key to delete.
        """
        try:
            result = self.redis_client.delete(key)
            if result == 1:
                print(f"Key '{key}' deleted successfully.")
            else:
                print(f"Key '{key}' does not exist.")
        except Exception as e:
            print(f"Failed to delete key '{key}': {e}")

    def key_exists(self, key):
        """
        Check if a key exists in Redis.

        :param key: The key to check.
        :return: True if the key exists, False otherwise.
        """
        try:
            return self.redis_client.exists(key) == 1
        except Exception as e:
            print(f"Failed to check existence of key '{key}': {e}")

    def set_ttl(self, key, ttl):
        """
        Set a TTL for an existing key.

        :param key: The key to set a TTL on.
        :param ttl: Time to Live in seconds.
        """
        try:
            result = self.redis_client.expire(key, ttl)
            if result:
                print(f"TTL for key '{key}' set to {ttl} seconds.")
            else:
                print(f"Failed to set TTL for key '{key}'. The key may not exist.")
        except Exception as e:
            print(f"Failed to set TTL for key '{key}': {e}")

    def get_ttl(self, key):
        """
        Get the TTL for a given key.

        :param key: The key to get TTL for.
        :return: TTL in seconds, -1 if the key has no expiration, -2 if the key does not exist.
        """
        try:
            ttl = self.redis_client.ttl(key)
            if ttl >= 0:
                print(f"TTL for key '{key}' is {ttl} seconds.")
            elif ttl == -1:
                print(f"Key '{key}' has no expiration.")
            elif ttl == -2:
                print(f"Key '{key}' does not exist.")
            return ttl
        except Exception as e:
            print(f"Failed to get TTL for key '{key}': {e}")

    def queue_chat_data(self, queue_name, data):
        """
        Add chat data to a Redis queue (list).

        :param queue_name: The name of the queue (list) to push the data onto.
        :param data: The chat data to queue (will be serialized to JSON).
        """
        try:
            serialized_data = json.dumps(data)
            self.redis_client.rpush(queue_name, serialized_data)
            print(f"Chat data added to queue '{queue_name}'.")
        except Exception as e:
            print(f"Failed to queue chat data to '{queue_name}': {e}")

    def get_queued_chat_data(self, queue_name):
        """
        Retrieve chat data from a Redis queue (list).

        :param queue_name: The name of the queue (list) to pop the data from.
        :return: The chat data from the queue (deserialized from JSON).
        """
        try:
            serialized_data = self.redis_client.lpop(queue_name)
            if serialized_data is not None:
                return json.loads(serialized_data)
            else:
                print(f"No data in queue '{queue_name}'.")
                return None
        except Exception as e:
            print(f"Failed to get chat data from queue '{queue_name}': {e}")

    def add_data(self, queue_name:str, data, ttl=None):
        try:
            self.set_key(f"{queue_name}", data, ttl)
            print(f"Chat data added with ID '{queue_name}'.")
        except Exception as e:
            print(f"Failed to add chat data with ID '{queue_name}': {e}")

    def get_data(self, queue_name:str):
        try:
            return self.get_key(f"{queue_name}")
        except Exception as e:
            print(f"Failed to get chat data with ID '{queue_name}': {e}")





if __name__ == '__main__':
    db = RedisClient()
    # db.set_key("test", "fuck this kid parker")
    print(db.get_key("test"))