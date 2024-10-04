from typing import overload
import redis
import json
from torch.cuda.nccl import unique_id

class RedisClient:
    def __init__(self, host='192.168.1.6', port=6379, db=0, password=None):
        """
        Initialize the Redis client.
        :param host: Redis server hostname (default: 'localhost')
        :param port: Redis server port (default: 6379)
        :param db: Redis database index (default: 0)
        :param password: Password for Redis server (default: None)
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
        self.connect()

    def connect(self):
        """Establish a connection to the Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password
            )
            self.redis_client.ping()  # Test connection
            print("Connected to Redis server.")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            raise

    def set_key(self, key, value, ttl=None):
        """
        Set a key-value pair in Redis with an optional TTL.

        :param key: The key to set.
        :param value: The value to set (will be serialized to JSON).
        :param ttl: Time to Live in seconds (optional).
        """
        try:
            serialized_value = json.dumps(value)
            if ttl:
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                self.redis_client.set(key, serialized_value)
            print(f"Key '{key}' set successfully.")
        except Exception as e:
            print(f"Failed to set key '{key}': {e}")
            raise

    def get_key(self, key):
        """
        Retrieve a value by key from Redis.

        :param key: The key to retrieve.
        :return: The value associated with the key (deserialized from JSON).
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                return json.loads(value)
            else:
                print(f"Key '{key}' does not exist.")
                return None
        except Exception as e:
            print(f"Failed to get key '{key}': {e}")
            raise

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
            raise

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
            raise

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
            raise

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
            raise


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
            raise


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
            raise

    def add_data(self, queue_name:str, data, ttl=None):
        try:
            self.set_key(f"{queue_name}", data, ttl)
            print(f"Chat data added with ID '{queue_name}'.")
        except Exception as e:
            print(f"Failed to add chat data with ID '{queue_name}': {e}")
            raise
    def get_data(self, queue_name:str):
        try:
            return self.get_key(f"{queue_name}")
        except Exception as e:
            print(f"Failed to get chat data with ID '{queue_name}': {e}")
            raise
    @overload
    def add_chat_data(self, chatId:str, messageId:str, data, ttl=None):
        try:
            self.set_key(f"{chatId}:{messageId}", data, ttl)
            print(f"Chat data added with ID '{unique_id}'.")
        except Exception as e:
            print(f"Failed to add chat data with ID '{unique_id}': {e}")
            raise

    def add_chat_data_by_id(self, unique_id, data, ttl=None):
        """
        Store chat data in Redis using a unique ID.

        :param unique_id: The unique ID used as the key.
        :param data: The chat data to store (will be serialized to JSON).
        :param ttl: Time to Live in seconds (optional).
        """
        try:
            self.set_key(unique_id, data, ttl)
            print(f"Chat data added with ID '{unique_id}'.")
        except Exception as e:
            print(f"Failed to add chat data with ID '{unique_id}': {e}")
            raise

    def get_chat_data_by_id(self, chatId:str, messageId:str):
        """
        Retrieve chat data from Redis using a unique ID.

        :param unique_id: The unique ID used as the key.
        :return: The chat data associated with the unique ID (deserialized from JSON).
        """
        try:
            return self.get_key(f"{chatId}:{messageId}")
        except Exception as e:
            print(f"Failed to get chat data with ID '{unique_id}': {e}")
            raise

    def get_chat_data_by_id(self, unique_id):
        """
        Retrieve chat data from Redis using a unique ID.

        :param unique_id: The unique ID used as the key.
        :return: The chat data associated with the unique ID (deserialized from JSON).
        """
        try:
            return self.get_key(unique_id)
        except Exception as e:
            print(f"Failed to get chat data with ID '{unique_id}': {e}")
            raise

class RaiCache(RedisClient):
    def cache_announcement(self, key_name, data, ttl=None):
        """Cache an announcement or message."""
        try:
            self.set_key(f"announcement:{key_name}", data, ttl)
            print(f"Announcement '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache announcement '{key_name}': {e}")
            raise

    def get_announcement(self, key_name):
        """Retrieve a cached announcement or message."""
        try:
            return self.get_key(f"announcement:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve announcement '{key_name}': {e}")
            raise

    def cache_weather_data(self, key_name, data, ttl=43200):
        """Cache weather data with a default TTL of 12 hours (43200 seconds)."""
        try:
            self.set_key(f"weather:{key_name}", data, ttl)
            print(f"Weather data '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache weather data '{key_name}': {e}")
            raise

    def get_weather_data(self, key_name):
        """Retrieve cached weather data."""
        try:
            return self.get_key(f"weather:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve weather data '{key_name}': {e}")
            raise

    def cache_chat_message(self, chat_id, message_id, data, ttl=None):
        """Cache a chat message."""
        try:
            key = f"chat:{chat_id}:{message_id}"
            self.set_key(key, data, ttl)
            print(f"Chat message '{key}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache chat message '{key}': {e}")
            raise

    def get_chat_message(self, chat_id, message_id):
        """Retrieve a cached chat message."""
        try:
            key = f"chat:{chat_id}:{message_id}"
            return self.get_key(key)
        except Exception as e:
            print(f"Failed to retrieve chat message '{key}': {e}")
            raise

    def cache_chromadb_query(self, key_name, data, ttl=None):
        """Cache a ChromaDB query and its results."""
        try:
            self.set_key(f"chromadb:{key_name}", data, ttl)
            print(f"ChromaDB query '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache ChromaDB query '{key_name}': {e}")
            raise

    def get_chromadb_query(self, key_name):
        """Retrieve a cached ChromaDB query and its results."""
        try:
            return self.get_key(f"chromadb:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve ChromaDB query '{key_name}': {e}")
            raise

    def cache_field_status(self, field_id, status, ttl=None):
        """Cache the status of a field (ON or OFF)."""
        try:
            self.set_key(f"field_status:{field_id}", status, ttl)
            print(f"Field status for '{field_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache field status '{field_id}': {e}")
            raise

    def get_field_status(self, field_id):
        """Retrieve the cached status of a field."""
        try:
            return self.get_key(f"field_status:{field_id}")
        except Exception as e:
            print(f"Failed to retrieve field status '{field_id}': {e}")
            raise

    def cache_game_schedule(self, game_id, data, ttl=None):
        """Cache a game schedule."""
        try:
            self.set_key(f"game_schedule:{game_id}", data, ttl)
            print(f"Game schedule '{game_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache game schedule '{game_id}': {e}")
            raise

    def get_game_schedule(self, game_id):
        """Retrieve a cached game schedule."""
        try:
            return self.get_key(f"game_schedule:{game_id}")
        except Exception as e:
            print(f"Failed to retrieve game schedule '{game_id}': {e}")
            raise

    def cache_team_standings(self, league_id, data, ttl=None):
        """Cache team standings for a league."""
        try:
            self.set_key(f"team_standings:{league_id}", data, ttl)
            print(f"Team standings for league '{league_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache team standings for league '{league_id}': {e}")
            raise

    def get_team_standings(self, league_id):
        """Retrieve cached team standings for a league."""
        try:
            return self.get_key(f"team_standings:{league_id}")
        except Exception as e:
            print(f"Failed to retrieve team standings for league '{league_id}': {e}")
            raise

    def cache_player_profile(self, player_id, data, ttl=None):
        """Cache a player's profile."""
        try:
            self.set_key(f"player_profile:{player_id}", data, ttl)
            print(f"Player profile '{player_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache player profile '{player_id}': {e}")
            raise

    def get_player_profile(self, player_id):
        """Retrieve a cached player's profile."""
        try:
            return self.get_key(f"player_profile:{player_id}")
        except Exception as e:
            print(f"Failed to retrieve player profile '{player_id}': {e}")
            raise

    def cache_practice_notification(self, team_id, data, ttl=None):
        """Cache a practice notification for a team."""
        try:
            self.set_key(f"practice_notification:{team_id}", data, ttl)
            print(f"Practice notification for team '{team_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache practice notification for team '{team_id}': {e}")
            raise

    def get_practice_notification(self, team_id):
        """Retrieve a cached practice notification for a team."""
        try:
            return self.get_key(f"practice_notification:{team_id}")
        except Exception as e:
            print(f"Failed to retrieve practice notification for team '{team_id}': {e}")
            raise



if __name__ == '__main__':
    db = RedisClient()
    # db.set_key("test", "fuck this kid parker")
    print(db.get_key("test"))