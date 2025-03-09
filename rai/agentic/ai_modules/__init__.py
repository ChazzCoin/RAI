from abc import abstractmethod
from typing import Any

from rai.agentic.ai_assistants.QCache import VectorCache
from rai.agentic.ai_assistants.QStore import VectorStore
from rai.assistant.connectors import rAI

rAI = rAI('openai')
rStore = VectorStore()
rCache = VectorCache()

class rModule:

    @staticmethod
    @abstractmethod
    def module_name() -> str: pass

    @staticmethod
    def chain_data(*args: Any) -> str:
        """
        Join provided arguments into a single string. Non-string types are converted to strings.
        """
        return "\n".join(str(arg) for arg in args)

    @staticmethod
    def r_engine() -> str: return rAI.CURRENT_ENGINE
    @staticmethod
    def r_switch_engine(engine:str): return rAI.switch_engine(engine)
    @staticmethod
    def rAI() -> rAI: return rAI
    @staticmethod
    def rStore() -> VectorStore: return rStore
    @staticmethod
    def rCache() -> VectorCache: return rCache
    @staticmethod
    def rRedis(): return rCache.redis_client
