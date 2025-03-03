import json

from rai.internal.redis_db import RedisClient


class PluginQueue(RedisClient):
    """
    RedisQueue is a plugin for AI agents to manage task queues using Redis.
    It leverages Redis lists to create a robust, namespaced queue system.

    Example:
        # Initialize a queue for an AI agent with a unique namespace "agent123:tasks"
        agent_queue = RedisQueue(queue_namespace="agent123:tasks", db=0)

        # Enqueue a task
        agent_queue.enqueue({"task": "process_data", "data": "example"})

        # Dequeue a task (non-blocking)
        task = agent_queue.dequeue()
        print(task)

        # Dequeue a task (blocking with a 5-second timeout)
        task = agent_queue.dequeue(block=True, timeout=5)
    """

    def __init__(self, queue_namespace: str, db: int = 0):
        """
        Initialize RedisQueue with a given namespace.

        :param queue_namespace: A unique namespace for this agent's queue.
        :param db: Redis database index.
        """
        super().__init__(db)
        self.queue_namespace = queue_namespace

    def _format_queue_name(self, sub_queue: str = None) -> str:
        """
        Format the queue name using the namespace and an optional sub-queue.

        :param sub_queue: Optional additional queue identifier.
        :return: A namespaced queue name.
        """
        if sub_queue:
            return f"{self.queue_namespace}:{sub_queue}"
        return self.queue_namespace

    def enqueue(self, item, sub_queue: str = None):
        """
        Add an item to the queue.

        :param item: The item to enqueue (will be JSON serialized if it is a dict).
        :param sub_queue: Optional sub-queue identifier.
        """
        q_name = self._format_queue_name(sub_queue)
        try:
            serialized_item = json.dumps(item) if isinstance(item, dict) else str(item)
            self.redis_client.rpush(q_name, serialized_item)
            print(f"Item enqueued to queue '{q_name}'.")
        except Exception as e:
            print(f"Failed to enqueue item to queue '{q_name}': {e}")

    def dequeue(self, sub_queue: str = None, block: bool = False, timeout: int = 0):
        """
        Remove and return the first item from the queue.

        :param sub_queue: Optional sub-queue identifier.
        :param block: Whether to block if the queue is empty (using BLPOP).
        :param timeout: Timeout in seconds for blocking pop.
        :return: The dequeued item, deserialized from JSON if applicable, or None if empty.
        """
        q_name = self._format_queue_name(sub_queue)
        try:
            if block:
                # Blocking pop from the left side with a timeout
                result = self.redis_client.blpop(q_name, timeout=timeout)
                if result:
                    _, item = result
                else:
                    return None
            else:
                item = self.redis_client.lpop(q_name)
            if item:
                try:
                    return json.loads(item)
                except Exception:
                    return item.decode("utf-8") if isinstance(item, bytes) else item
            else:
                print(f"Queue '{q_name}' is empty.")
                return None
        except Exception as e:
            print(f"Failed to dequeue from queue '{q_name}': {e}")
            return None

    def peek(self, index: int = 0, sub_queue: str = None):
        """
        Peek at an item in the queue without removing it.

        :param index: The index of the item to peek at (default is 0 for the front of the queue).
        :param sub_queue: Optional sub-queue identifier.
        :return: The item at the specified index, deserialized if applicable.
        """
        q_name = self._format_queue_name(sub_queue)
        try:
            item = self.redis_client.lindex(q_name, index)
            if item:
                try:
                    return json.loads(item)
                except Exception:
                    return item.decode("utf-8") if isinstance(item, bytes) else item
            else:
                print(f"No item found at index {index} in queue '{q_name}'.")
                return None
        except Exception as e:
            print(f"Failed to peek in queue '{q_name}': {e}")
            return None

    def queue_size(self, sub_queue: str = None):
        """
        Get the current size of the queue.

        :param sub_queue: Optional sub-queue identifier.
        :return: The number of items in the queue.
        """
        q_name = self._format_queue_name(sub_queue)
        try:
            size = self.redis_client.llen(q_name)
            return size
        except Exception as e:
            print(f"Failed to get size of queue '{q_name}': {e}")
            return 0

    def clear_queue(self, sub_queue: str = None):
        """
        Clear all items from the queue.

        :param sub_queue: Optional sub-queue identifier.
        """
        q_name = self._format_queue_name(sub_queue)
        try:
            self.redis_client.delete(q_name)
            print(f"Queue '{q_name}' cleared.")
        except Exception as e:
            print(f"Failed to clear queue '{q_name}': {e}")
