import json
from abc import abstractmethod
from enum import Enum
from typing import List

from rai.internal.clients.redis_client import RedisDB


class ToolLog:
    voice: List[str] = []
    thoughts: List[str] = []
    ioRedis = RedisDB()
    class LogType(Enum):
        THOUGHTS = "thoughts"
        VOICE = "voice"

    @abstractmethod
    def log_key(self) -> str:
        """Should return a unique Redis key for caching thoughts."""
        pass
    def _get_log_key(self, name:str=LogType.THOUGHTS) -> str:
        return f"log:{name}:{self.log_key}"

    def load_voice(self):
        """Load the thoughts list from Redis cache."""
        cached = self.ioRedis.client.get(self._get_log_key("voice"))
        if cached:
            try:
                self.voice = json.loads(cached)
            except json.JSONDecodeError:
                self.voice = []
        else:
            self.voice = []
        return self.voice
    def _cache_voice(self):
        """Helper method to cache the current thoughts list to Redis."""
        self.ioRedis.client.set(self._get_log_key("voice"), json.dumps(self.voice))
    def log_voice(self, *data: str) -> str:
        """Log messages to the assistant log chain and update the Redis cache."""
        for line in data:
            info_message = "Speaking... " + str(line)
            print(info_message)
            self.voice.append(info_message)
        self._cache_voice()
        return str(data)

    def load_thoughts(self):
        """Load the thoughts list from Redis cache."""
        cached = self.ioRedis.client.get(self._get_log_key())
        if cached:
            try:
                self.thoughts = json.loads(cached)
            except json.JSONDecodeError:
                self.thoughts = []
        else:
            self.thoughts = []
        return self.thoughts
    def _cache_thoughts(self):
        """Helper method to cache the current thoughts list to Redis."""
        self.ioRedis.client.set(self._get_log_key(), json.dumps(self.thoughts))
    def log_thought(self, *data: str) -> str:
        """Log messages to the assistant log chain and update the Redis cache."""
        for line in data:
            info_message = "Thinking... " + str(line)
            print(info_message)
            self.thoughts.append(info_message)
        self._cache_thoughts()
        return str(data)
    def add_problem(self, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix and update the Redis cache."""
        for line in data:
            error_message = "Eh, I'm seeing a Problem..." + str(line)
            print(error_message)
            self.thoughts.append(error_message)
        self._cache_thoughts()
        return str(data)
    def get_thoughts(self) -> List[str]:
        """Retrieve the assistant log as a list of strings."""
        return self.thoughts
    def inject_thoughts_tag(self) -> str:
        """Retrieve the assistant log as a single string."""
        return f"""
            <THOUGHTS_LOG>
                {str(self.thoughts)}
            </THOUGHTS_LOG>
        """
    def inject_voice_tag(self) -> str:
        """Retrieve the assistant log as a single string."""
        return f"""
            <VOICE_LOG>
                {str(self.voice)}
            </VOICE_LOG>
        """



ASSISTANT_LOG_CHAIN = []

class mAssistLog:

    @classmethod
    def assistant_log(cls, *data: str) -> str:
        """Log messages to the assistant log chain."""
        for line in data:
            info_message = f"r{cls.__name__}: INFO: " + line
            print(info_message)
            ASSISTANT_LOG_CHAIN.append(info_message)
        return str(data)

    @classmethod
    def assistant_error_log(cls, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix."""
        for line in data:
            error_message = f"r{cls.__name__}: ERROR: " + line
            print(error_message)
            ASSISTANT_LOG_CHAIN.append(error_message)
        return str(data)

    @staticmethod
    def get_assistant_log() -> List[str]:
        """Retrieve the assistant log as a list of strings."""
        return ASSISTANT_LOG_CHAIN

    @staticmethod
    def get_assistant_log_str() -> str:
        """Retrieve the assistant log as a single string."""
        return str(ASSISTANT_LOG_CHAIN)



