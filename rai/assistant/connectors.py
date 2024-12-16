from typing import Dict, Type, Any
from typing import List, Optional
from rai.assistant.ai_models import AiModels
from rai.assistant.engines import Ollama, OpenAI, AiEngine


class RaiAi:
    MODELS = AiModels
    OLLAMA = Ollama()
    OPENAI = OpenAI()

    def __init__(self):
        self.engines: Dict[str, AiEngine] = {}
        self.initialize_engines()

    def initialize_engines(self):
        self.engines['openai'] = self.OPENAI
        self.engines['ollama'] = self.OLLAMA

    def get_engine(self, name: str) -> AiEngine:
        engine = self.engines.get(name)
        if not engine:
            raise ValueError(f"Engine '{name}' is not initialized.")
        return engine

    def generate(self, engine_name: str, user_prompt: str, system_prompt: str="You are a useful assistant.", response_format: Optional[Dict[str, Any]] = None):
        engine = self.get_engine(engine_name)
        return engine.generate(system_prompt, user_prompt, response_format=response_format)
    def generate_embeddings(self, engine_name: str, content: str, model_override: Optional[str] = None):
        engine = self.get_engine(engine_name)
        return engine.generate_embeddings(content, model_override)


