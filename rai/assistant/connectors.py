import threading
from typing import Dict, Type

import numpy as np
from F import DICT
from pydantic import BaseModel

from rai.agentic.ai_tools.text_tools.text_formats import aiTextFormats
from rai.agentic.ai_tools.text_tools.text_functions import aiTextFunctions
from rai.agentic.ai_tools.text_tools.text_prompts import aiTextPrompts
from rai.assistant.engines import OllamaEngine, OpenAiEngine, AiModels, FusedAI
from rai.ingest.utilities.text_data import schedule_text

TEXT_TOOL_REGISTRY = {}

def register_text_tool(name: str):
    def decorator(cls):
        TEXT_TOOL_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator


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

    """ Tools """
    @classmethod
    def ollama_generate(cls, user:str, system:str, model=AiModels.DEFAULT_OLLAMA):
        return cls().get_engine("ollama").generate(
            user=user,
            system=system,
            model=model
        )
    @classmethod
    def ollama_reasoning(cls, user:str, system:str, model=AiModels.DEFAULT_OLLAMA_REASONING):
        return cls().get_engine("ollama").generate(
            user=user,
            system=system,
            model=model
        )
    @classmethod
    def ollama_decision(cls, user:str, system:str, functions: [dict], raw_result:bool=True):
        return cls().get_engine("ollama").generate_function(
            user=user,
            system=system,
            functions=functions,
            raw_result=raw_result
        )
    @classmethod
    def gen(cls, user:str, system:str):
        return cls().engine.generate(
            user=user,
            system=system
        )
    @classmethod
    def formatter(cls, text, model: Type[BaseModel]) -> Type[BaseModel]:
        return cls().engine.generate_format(
            user=text,
            system="Extract the necessary data/attributes for the provided response format.",
            format=model
        )
    @classmethod
    def decision(cls, user:str, system:str, functions: [dict], raw_result:bool=True, response_only=False) -> Type[BaseModel]:
        return cls().engine.generate_function(
            user=user,
            system=system,
            functions=functions,
            raw_result=raw_result,
            response_only=response_only
        )


    """ BASE """
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

    @classmethod
    def get_registry(cls):
        return TEXT_TOOL_REGISTRY

    @classmethod
    def get_tool_names(cls):
        return list(TEXT_TOOL_REGISTRY.keys())

    @classmethod
    def tool(cls, name: str, user_prompt: str = "", system_prompt: str = None, sub=False):
        agent_classes = TEXT_TOOL_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt, sub=sub)

    @classmethod
    async def tool_async(cls, name: str, user_prompt: str, system_prompt: str = None, sub=False):
        agent_classes = TEXT_TOOL_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(user_prompt=user_prompt, system_prompt=system_prompt, sub=sub)

    @classmethod
    def tools(cls, *names: str, user_prompt: str, system_prompt: str = None):
        pipe_results = {}

        def thread_runner(user_prompt, name, system_prompt):
            agent_classes = TEXT_TOOL_REGISTRY.get(name)
            if not agent_classes:
                pipe_results[name] = None
                return
            cls.name = name
            agent_cls = agent_classes[0]
            agent_instance = agent_cls()
            pipe_results[name] = agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt)

        # Create and start a thread for each collection
        threads = []
        for name in names:
            thread = threading.Thread(target=thread_runner, args=(user_prompt, name, system_prompt))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        return pipe_results

    # @abstractmethod
    def type(self):
        pass

    # @abstractmethod
    def parse(self, result):
        pass

    def pipeline_system_prompt(self):
        return aiTextPrompts.pipeline(self.name)

    def prompter(self, user_prompt):
        return f"USER PROMPT:\n{user_prompt}"

    def run(self, user_prompt, system_prompt=None, image=None, sub=False):
        try:
            if self.type() == "format":
                return self.parse(self.engine.generate_format(
                    user=self.prompter(user_prompt),
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt,
                    format=aiTextFormats.format(self.name)
                ))
            elif self.type() == "function":
                return self.parse(self.engine.generate_function(
                    user=self.prompter(user_prompt),
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt,
                    functions=aiTextFunctions.function(self.name, sub=sub)
                ))
            elif self.type() == "generate":
                return self.parse(self.engine.generate(
                    user=user_prompt,
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

    async def run_async(self, user_prompt, system_prompt=None, image=None, sub=False):
        try:
            if self.type() == "format":
                return self.parse(await self.engine.generate_format_async(
                    user=self.prompter(user_prompt),
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt,
                    format=aiTextFormats.format(self.name)
                ))
            elif self.type() == "function":
                return self.parse(await self.engine.generate_function_async(
                    user=self.prompter(user_prompt),
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt,
                    functions=aiTextFunctions.function(self.name, sub=sub)
                ))
            elif self.type() == "generate":
                return self.parse(await self.engine.generate_async(
                    user=user_prompt,
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt
                ))
            elif self.type() == "image":
                return self.parse(self.engine.generate_async(
                    user=user_prompt,
                    system=self.pipeline_system_prompt() if not system_prompt else system_prompt,
                    image=image
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

LLM = rAI()

