
from rai.internal.redis_db import RedisClient


class PluginState(RedisClient):
    """
    RedisState is a plugin for AI agents to manage their state using Redis.
    It provides a namespaced key-value store to persist state across runs.

    Example:
        # Initialize state for an AI agent with a unique namespace "agent123"
        agent_state = RedisState(state_namespace="agent123", db=0, default_ttl=3600)

        # Set some state information
        agent_state.set_state("conversation", {"last_message": "Hello, world!"})

        # Retrieve the state
        state = agent_state.get_state("conversation")
        print(state)
    """

    def __init__(self, state_namespace: str):
        """
        Initialize RedisState with a given namespace.

        :param state_namespace: A unique namespace for this agent's state.
        :param db: Redis database index.
        :param default_ttl: Default Time To Live (in seconds) for state keys.
        """
        super().__init__()
        self.state_namespace = state_namespace
        self.default_ttl = None

    def _format_key(self, key: str) -> str:
        """
        Format the key by prefixing it with the namespace.

        :param key: The raw key.
        :return: A namespaced key string.
        """
        return f"{self.state_namespace}:{key}"

    def set_state(self, key: str, value, ttl: int = None):
        """
        Set a state value under a namespaced key.

        :param key: The state key.
        :param value: The value to store (will be JSON serialized if it's a dict).
        :param ttl: Optional TTL (in seconds) for this state entry; falls back to default_ttl if not provided.
        """
        namespaced_key = self._format_key(key)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        self.set_key(namespaced_key, value, effective_ttl)

    def get_state(self, key: str, default=None):
        """
        Retrieve a state value using the namespaced key.

        :param key: The state key.
        :param default: A default value to return if the key does not exist.
        :return: The stored state value.
        """
        namespaced_key = self._format_key(key)
        return self.get_key(namespaced_key, default)

    def delete_state(self, key: str):
        """
        Delete a state entry.

        :param key: The state key.
        """
        namespaced_key = self._format_key(key)
        self.delete_key(namespaced_key)

    def update_state(self, key: str, new_values: dict, ttl: int = None):
        """
        Update a state value (expected to be a dictionary) by merging with new key/value pairs.

        :param key: The state key.
        :param new_values: A dictionary with values to update.
        :param ttl: Optional TTL (in seconds) for this state entry after updating.
        :raises ValueError: if the current state is not a dictionary.
        """
        current_state = self.get_state(key, {})
        if not isinstance(current_state, dict):
            raise ValueError("Current state is not a dictionary; cannot update.")
        current_state.update(new_values)
        self.set_state(key, current_state, ttl)

    def clear_all_state(self):
        """
        Clear all state entries under the current namespace.
        """
        pattern = self._format_key("*")
        keys = self.keys(pattern)
        if keys:
            for key in keys:
                self.delete_key(key)
