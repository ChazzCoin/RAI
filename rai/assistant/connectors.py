from typing import Dict, Type

import numpy as np
from F import DICT
from pydantic import BaseModel

from rai.assistant.engines import OllamaEngine, OpenAiEngine, AiModels, FusedAI

class rAI:
    CURRENT_ENGINE = 'openai'
    DEFAULT_MODEL: str = AiModels.DEFAULT_OLLAMA
    KEY: str = ""
    TEMPERATURE: float = 0.5
    TOP_K: int = 10
    FREQUENCY_PENALTY: float = 0.5

    MODELS = AiModels
    OLLAMA = OllamaEngine()
    OPENAI = OpenAiEngine()

    MODEL_DEFAULT = AiModels.DEFAULT_OPENAI
    MODEL_FUNCTION = AiModels.DEFAULT_OPENAI
    MODEL_FORMAT = AiModels.DEFAULT_OPENAI

    # @staticmethod
    # def text_tool(name, user_prompt): return rTextTools.tool(name, user_prompt)
    # @staticmethod
    # def image_tool(name, user_prompt): return rImageTools.tool(name, user_prompt)
    #
    # TEXT_TOOL_PROMPTS = aiTextPrompts
    # TEXT_TOOL_FORMATS = aiTextFormats
    # TEXT_TOOL_FUNCTIONS = aiTextFunctions
    #
    # IMAGE_TOOL_PROMPTS = aiImagePrompts
    # IMAGE_TOOL_FORMATS = aiImageFormats
    # IMAGE_TOOL_FUNCTIONS = aiImageFunctions

    def __init__(self, engine_name:str='openai'):
        self.engines: Dict[str, FusedAI] = {}
        self.initialize_engines()
        self.switch_engine(engine_name)

    def initialize_engines(self):
        if not self.engines: self.engines: Dict[str, FusedAI] = {}
        self.engines['openai'] = self.OPENAI
        self.engines['ollama'] = self.OLLAMA

    @property
    def engine(self) -> FusedAI:
        return self.engines.get(self.CURRENT_ENGINE)

    def get_engine(self, override:str=None) -> FusedAI:
        return self.engines.get(self.CURRENT_ENGINE if override is None else override)

    def switch_engine(self, engine_name: str):
        self.CURRENT_ENGINE = engine_name
        return self.engine.switch_engine(engine_name)

    def embed(self, text:str):
        return self.engine.generate_embeddings(text)

    def embed_for_cache(self, query) -> bytes:
        embeddings = self.engine.generate_embeddings(query)
        query_embedding = np.array(embeddings, dtype=np.float32)
        return query_embedding.tobytes()

    def generate(self, user: str, system: str, image=None):
        return self.engine.generate(user, system, image)

    def generate_function(self, user: str, system: str, functions: [dict], image=None, raw_result=False):
        result = self.engine.generate_function(user, system, functions, image, raw_result)
        if raw_result: return result
        return self.parse_function_names(result)

    def generate_format(self, user: str, system: str, format: Type[BaseModel], image=None):
        result = self.engine.generate_format(user, system, format, image)
        return result

    async def generate_function_async(self, user: str, system: str, functions: [dict], image=None):
        result = await self.engine.generate_function_async(user, system, functions, image)
        return self.parse_function_names(result)

    @staticmethod
    def parse_function_names(result):
        if type(result) in [list, tuple]:
            parsed = []
            for item in result:
                name = DICT.get("name", item, None)
                if name: parsed.append(name)
            return parsed
        else:
            return result

    def set_temperature(self, temp: float):
        self.TEMPERATURE = temp

    def set_strict(self):
        self.TEMPERATURE = 0.0
        self.TOP_K = 10
        self.FREQUENCY_PENALTY = 0.5

    def set_loose(self):
        self.TEMPERATURE = 2.0
        self.TOP_K = 40
        self.FREQUENCY_PENALTY = 1.0

    def set_balanced(self):
        self.TEMPERATURE = 1.0
        self.TOP_K = 20
        self.FREQUENCY_PENALTY = 0.0

    def set_default_model(self, model: str):
        self.DEFAULT_MODEL = model

