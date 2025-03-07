import json
from typing import Any, List

from rai.internal.redis_db import RedisClient


class PluginAgentCache(RedisClient):
    """
    Extension of the Redis client to support caching agent responses
    and managing a central queue of agent configurations.

    Redis is used only as an add-on; if Redis is not available, operations
    will fail gracefully, and the agent runner will continue to run.
    """

    def __init__(self, db: int = 0, queue_name: str = "rai_agent_queue"):
        super().__init__(db=db)
        self.queue_name = queue_name

    def is_redis_available(self) -> bool:
        """
        Check whether Redis is available.
        """
        try:
            return self.redis_client is not None and self.redis_client.ping()
        except Exception as e:
            print(f"Redis unavailable: {e}")
            return False

    # ------------------------------
    # Caching agent responses
    # ------------------------------
    def cache_agent_response(self, agent_id: str, response_type: str, response: Any, ttl: int = None):
        """
        Cache an agent's response (e.g., text, image, audio, or video).
        The key is composed of the agent ID and the response type.
        """
        if not self.is_redis_available():
            print("Skipping caching; Redis is not available.")
            return

        key = f"agent_response:{agent_id}:{response_type}"
        try:
            self.set_key(key, response, ttl)
            print(f"Cached response under key '{key}'.")
        except Exception as e:
            print(f"Failed to cache agent response '{key}': {e}")

    def get_agent_response(self, agent_id: str, response_type: str) -> Any:
        """
        Retrieve a cached response for the given agent and response type.
        """
        if not self.is_redis_available():
            print("Skipping retrieval; Redis is not available.")
            return None

        key = f"agent_response:{agent_id}:{response_type}"
        try:
            return self.get_key(key)
        except Exception as e:
            print(f"Failed to retrieve agent response '{key}': {e}")
            return None

    def aggregate_agent_responses(self, agent_ids: List[str], response_type: str) -> str:
        """
        Aggregate responses from multiple agents of the specified response type.
        For example, if response_type is 'text', the function concatenates
        each agent's text response into one large generation.
        """
        aggregated = ""
        for agent_id in agent_ids:
            resp = self.get_agent_response(agent_id, response_type)
            if resp:
                aggregated += str(resp) + "\n"
        return aggregated.strip()

    # ------------------------------
    # Queue management for agent configurations
    # ------------------------------
    def add_agent_config_to_queue(self, config: dict):
        """
        Add an agent configuration (as a dict) to the Redis queue.
        If Redis is not available, this method fails gracefully.
        """
        if not self.is_redis_available():
            print("Skipping queue addition; Redis is not available.")
            return

        try:
            # Use the queue_chat_data method from your base client to push onto the list.
            # Here, we treat the queue as a list stored under self.queue_name.
            serialized_config = json.dumps(config)
            self.redis_client.rpush(self.queue_name, serialized_config)
            print(f"Agent config added to queue '{self.queue_name}'.")
        except Exception as e:
            print(f"Failed to add agent config to queue: {e}")

    def pop_agent_config_from_queue(self) -> dict:
        """
        Pop an agent configuration from the Redis queue.
        If no configuration exists or if Redis is not available, returns None.
        """
        if not self.is_redis_available():
            print("Skipping queue pop; Redis is not available.")
            return None

        try:
            serialized_config = self.redis_client.lpop(self.queue_name)
            if serialized_config:
                config = json.loads(serialized_config)
                print(f"Popped agent config from queue '{self.queue_name}'.")
                return config
            else:
                print(f"No agent config in queue '{self.queue_name}'.")
                return None
        except Exception as e:
            print(f"Failed to pop agent config from queue: {e}")
            return None
