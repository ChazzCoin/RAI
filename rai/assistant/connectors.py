from typing import Dict
from rai.agents.Tools import RaiFunctionCategories
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


if __name__ == '__main__':
    rai = RaiAi()
    ai = rai.get_engine('openai')
    print(ai.generate_function("How do I sign my child up to play and then order their uniforms?", "You are a youth soccer club assistant and RAG Master.", RaiFunctionCategories))