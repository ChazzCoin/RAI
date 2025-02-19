import threading
import json
from typing import Callable

from rai.internal.redisdb import RedisClient


from F.LOG import Log
Log = Log("Redis Messenger Client")

class RedisMessengerCenter(RedisClient):
    """
    A robust and production-ready Pub/Sub Messenger Center built on top of RedisClient.
    Responsible for publishing messages to channels and subscribing to channels to receive messages.
    """
    def __init__(self, db: int = 0):
        super().__init__(db)
        # Create a pubsub object with subscription messages filtered out.
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        # Dictionary to keep track of subscription threads by channel.
        self.subscriber_threads = {}

    def publish_message(self, channel: str, message, ttl: int = None):
        try:
            if not isinstance(message, str):
                message = json.dumps(message)
            # Publish returns the number of subscribers that received the message.
            subscriber_count = self.redis_client.publish(channel, message)
            Log.s(f"Published message to channel '{channel}'. Subscriber count: {subscriber_count}")
        except Exception as e:
            Log.e(f"Failed to publish message to channel '{channel}': {e}")
            raise

    def subscribe_channel(self, channel: str, callback: Callable[[str, any], None]):
        def listener():
            try:
                self.pubsub.subscribe(channel)
                Log.s(f"Subscribed to channel '{channel}'.")
                for message in self.pubsub.listen():
                    # We only process messages of type 'message'
                    if message.get("type") == "message":
                        raw_data = message.get("data")
                        try:
                            # Try to deserialize JSON payloads
                            data = json.loads(raw_data)
                        except Exception:
                            data = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
                        Log.s(f"Received message on channel '{channel}': {data}")
                        callback(channel, data)
            except Exception as e:
                Log.e(f"Error in listener for channel '{channel}': {e}")

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
        self.subscriber_threads[channel] = thread
        return thread

    def unsubscribe_channel(self, channel: str):
        try:
            self.pubsub.unsubscribe(channel)
            Log.s(f"Unsubscribed from channel '{channel}'.")
            if channel in self.subscriber_threads:
                del self.subscriber_threads[channel]
        except Exception as e:
            Log.e(f"Failed to unsubscribe from channel '{channel}': {e}")
            raise

    def unsubscribe_all(self):
        try:
            channels = list(self.subscriber_threads.keys())
            if channels:
                self.pubsub.unsubscribe(*channels)
                Log.s(f"Unsubscribed from all channels: {channels}")
                self.subscriber_threads.clear()
            else:
                Log.s("No channels to unsubscribe from.")
        except Exception as e:
            Log.e(f"Failed to unsubscribe from all channels: {e}")
            raise

    def listen(self):
        try:
            for message in self.pubsub.listen():
                if message.get("type") == "message":
                    Log.s(f"Received message: {message}")
        except Exception as e:
            Log.e(f"Error while listening for messages: {e}")
            raise
