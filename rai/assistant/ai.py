import json
from abc import abstractmethod, ABC
import requests
from rai import app
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional


class EmbeddingsModels:
    OPENAI = "text-embedding-ada-002"
    OLLAMA = "nomic-embed-text"


class AiEngine(ABC):
    engines: Dict[str, Type['AiEngine']] = {}
    KEY:str = ""

    def __init_subclass__(cls, *, engine: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if not engine:
            raise ValueError("Subclasses must define an 'engine' name.")
        cls.engine = engine
        AiEngine.engines[engine] = cls
    @abstractmethod
    def headers(self)-> Dict[str, str]: pass
    @abstractmethod
    def payload(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None): pass
    @abstractmethod
    def payload_embeddings(self, content: str, model_override: Optional[str] = None): pass
    @abstractmethod
    def route(self, route: str = "") -> str: pass
    @abstractmethod
    def default_model(self, override: Optional[str] = None) -> str: pass
    @abstractmethod
    def embeddings_model(self) -> str: pass
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None): pass
    @abstractmethod
    def generate_embeddings(self, content: str, model_override: Optional[str] = None): pass


class OpenAI(AiEngine, engine="openai"):
    GPT_4 = "gpt-4"
    GPT_4o = "gpt-4o"
    GPT_4o_mini = "gpt-4o-mini"
    URL = "https://api.openai.com/v1"

    def __init__(self, default_model: Optional[str] = None, embedding_model: Optional[str] = None):
        self.KEY = app.state.config.OPENAI_API_KEY
        self._default_model = default_model or self.GPT_4o_mini
        self._embedding_model = embedding_model or EmbeddingsModels.OPENAI

    def route(self, route: str = "") -> str:
        return f"{self.URL}{route}"

    def default_model(self, override: Optional[str] = None) -> str:
        return override or self._default_model

    def embeddings_model(self) -> str:
        return self._embedding_model
    def payload(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None):
        return {
            'model': self.default_model(override=model_override),  # Use 'gpt-4' if available
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': 0.7,
        }

    def headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.KEY}',
        }
    def payload_embeddings(self, content, model_override: Optional[str] = None):
        return {
            'model': self.embeddings_model() if not model_override else model_override,
            'input': content
        }

    def generate_embeddings(self, content: str, model_override: Optional[str] = None):
        """Asynchronously get embeddings from OpenAI API."""
        headers = self.headers()
        payload = self.payload_embeddings(content)
        resp = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers=headers,
            json=payload
        )
        if resp.status_code != 200:
            error = resp.json()
            raise Exception(f"Error from OpenAI API: {error}")
        response_data = resp.json()
        embedding = response_data['data'][0]['embedding']
        return embedding

    def generate(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None):
        """Asynchronously get chat completion from OpenAI API."""
        payload = self.payload(system_prompt, user_prompt, model_override)
        headers = self.headers()
        resp = requests.post(self.route("/chat/completions"), headers=headers, json=payload)
        if resp.status_code != 200:
            error = resp.json()
            raise Exception(f"Error from OpenAI API: {error}")
        response_data = resp.json()
        assistant_message = response_data['choices'][0]['message']['content']
        return assistant_message

class Ollama(AiEngine, engine="ollama"):
    LLAMA_3B_LATEST = "llama3:latest"
    LLAMA_CODER_34B = "codellama:34b"

    def __init__(self, default_model: Optional[str] = None, embedding_model: Optional[str] = None):
        self.host = app.state.config.OLLAMA_HOST
        self.port = app.state.config.OLLAMA_PORT
        self._default_model = default_model or self.LLAMA_3B_LATEST
        self._embedding_model = embedding_model or EmbeddingsModels.OLLAMA

    def route(self, route: str = "") -> str:
        return f"http://{self.host}:{self.port}{route}"

    def default_model(self, override: Optional[str] = None) -> str:
        return override or self._default_model

    def embeddings_model(self) -> str:
        return self._embedding_model

    def headers(self) -> Dict[str, str]:
        return {'Content-Type': 'application/json'}

    def payload(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None):
        return json.dumps({
            "model": self.default_model(override=model_override),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        })

    def payload_embeddings(self, content, model_override: Optional[str] = None):
        return json.dumps({
            'model': self.embeddings_model() if not model_override else model_override,
            'input': content
        })
    def generate_embeddings(self, content: str, model_override: Optional[str] = None):
        if not content:
            print("Prompt must be provided.")
            raise ValueError("Prompt must be provided.")
        try:
            response = requests.post(
                self.route("/api/embed"),
                headers=self.headers(),
                data=self.payload_embeddings(content),
                timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses
            data = response.json()
            if 'embeddings' in data:
                return data.get('embeddings', [])
            else:
                print("Embedding not found in the response.")
                raise ValueError("Embedding not found in the response.")
        except Exception as err:
            print(f"An unexpected error occurred: {err}")
            raise

    def generate(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None):
        payload = self.payload(system_prompt, user_prompt, model_override)
        response = requests.post(self.route("/api/chat"), headers=self.headers(), data=payload)
        if response.status_code == 200:
            response_data = response.json()
            return response_data['message']['content']
        else:
            if response: return response
            return {"error": f"Request failed with status code {response.status_code}"}

class RaiAi:
    EMBEDDINGS = EmbeddingsModels()
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

    def generate(self, engine_name: str, user_prompt: str, system_prompt: str="You are a useful assistant."):
        engine = self.get_engine(engine_name)
        return engine.generate(system_prompt, user_prompt)
    def generate_embeddings(self, engine_name: str, content: str, model_override: Optional[str] = None):
        engine = self.get_engine(engine_name)
        return engine.generate_embeddings(content, model_override)


