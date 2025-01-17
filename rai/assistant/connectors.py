from typing import Dict

from F import DICT

from rai.assistant.engines import OllamaEngine, OpenAiEngine, AiModels, FusedAI


class RaiAi:
    CURRENT_ENGINE = 'openai'
    DEFAULT_MODEL: str = AiModels.DEFAULT_OLLAMA
    KEY: str = ""
    TEMPERATURE: float = 0.5
    TOP_K: int = 10
    FREQUENCY_PENALTY: float = 0.5

    MODELS = AiModels
    OLLAMA = OllamaEngine()
    OPENAI = OpenAiEngine()

    def __init__(self, engine_name:str='openai'):
        self.engines: Dict[str, FusedAI] = {}
        self.initialize_engines()
        self.switch_engine(engine_name)

    def initialize_engines(self):
        self.engines['openai'] = self.OPENAI
        self.engines['ollama'] = self.OLLAMA

    @property
    def engine(self) -> FusedAI:
        return self.engines.get(self.CURRENT_ENGINE)

    def get_engine(self, override:str=None) -> FusedAI:
        return self.engines.get(self.CURRENT_ENGINE if override is None else override)

    def switch_engine(self, engine_name: str):
        if engine_name in self.engines.keys():
            self.CURRENT_ENGINE = engine_name
        else:
            return f"Engine [ {engine_name} ] Not Supported."

    def generate_function(self, user: str, system: str, functions: [dict]):
        result = self.engine.generate_function(user, system, functions)
        return self.parse_function_names(result)

    async def generate_function_async(self, user: str, system: str, functions: [dict]):
        result = await self.engine.generate_function_async(user, system, functions)
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


