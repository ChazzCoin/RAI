from abc import abstractmethod
from typing import Type, Any

from pydantic import BaseModel

from rai.agentic.ai_assistants.QCache import VectorCache
from rai.agentic.ai_assistants.QStore import VectorStore
from rai.agentic.ai_tools.image_tools.r_tools import rImageTools
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI

rAI = rAI('openai')
rStore = VectorStore()
rCache = VectorCache()

class rModule:

    class AssistResponse(BaseModel):
        prefix: str
        session_id: str
        answer: str
        data: Any

    @staticmethod
    @abstractmethod
    def module_name() -> str: pass

    @staticmethod
    @abstractmethod
    def _required_model() -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        pass

    @staticmethod
    def tag_data(tag:str, data:str): return f"<{str(tag).capitalize()}>\n {data} \n</{str(tag).capitalize()}"

    @staticmethod
    def chain_data(*args: Any) -> str:
        """
        Join provided arguments into a single string. Non-string types are converted to strings.
        """
        return "\n".join(str(arg) for arg in args)

    def ask_ai_to_parse_text_to_required_model(self, text: str) -> Type[BaseModel]:
        return rTextTools.formatter(text, self._required_model())

    @staticmethod
    def r_text_tools() -> Type[rTextTools]: return rTextTools
    @staticmethod
    def r_image_tools() -> Type[rImageTools]: return rImageTools
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


