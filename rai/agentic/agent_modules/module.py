import asyncio
from abc import abstractmethod, ABC
from typing import Type, Any
from pydantic import BaseModel
from rai.agentic.ai_assistants.QCache import vCACHE
from rai.agentic.ai_assistants.QStore import vSTORE
from rai.agentic.ai_modules.map import ToolMap
from rai.agentic.ai_modules.query import QueryModule
from rai.assistant.connectors import LLM, rAI
from rai.ingest.utilities.TextUtils import TextProcessor


class ToolModule(ToolMap, QueryModule, ABC):


    class ToolResponse(BaseModel):
        prefix: str
        session_id: str
        answer: str
        data: Any

    @staticmethod
    @abstractmethod
    def module_name() -> str: pass

    @staticmethod
    def response_model() -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        return ToolModule.ToolResponse

    @staticmethod
    def tag_data(tag:str, data:str): return f"<{str(tag).capitalize()}>\n {data} \n</{str(tag).capitalize()}"

    @staticmethod
    def chain_data(*args: Any) -> str:
        return "\n".join(str(arg) for arg in args)

    def ask_ai_to_parse_text_to_required_model(self, text: str) -> Type[BaseModel]:
        return self.llm().formatter(text, self.response_model())

    @staticmethod
    def t_processor() -> Type[TextProcessor]: return TextProcessor
    @staticmethod
    def r_engine() -> str: return LLM.CURRENT_ENGINE
    @staticmethod
    def r_switch_engine(engine:str): return LLM.switch_engine(engine)
    @property
    def think(self) -> 'rAI': return LLM
    @staticmethod
    def llm() -> 'rAI': return LLM
    @staticmethod
    def rStore() -> vSTORE: return vSTORE
    @staticmethod
    def rCache() -> vCACHE: return vCACHE
    @staticmethod
    def rRedis(): return vCACHE.redis_client


