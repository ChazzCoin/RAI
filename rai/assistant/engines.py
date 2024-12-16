import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type, Any
import ollama
import requests
from rai import app
from rai.assistant.connectors import AiModels
from rai.assistant.models import AiResponse


class AiEngine(ABC):
    engines: Dict[str, Type['AiEngine']] = {}
    DEFAULT_MODEL:str = AiModels.DEFAULT_OLLAMA
    KEY:str = ""
    TEMPERATURE:float = 0.5
    TOP_K: int = 10
    FREQUENCY_PENALTY: float = 0.5

    def __init_subclass__(cls, *, engine: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if not engine:
            raise ValueError("Subclasses must define an 'engine' name.")
        cls.engine = engine
        # cls.set_balanced()
        AiEngine.engines[engine] = cls

    def set_temperature(self, temp:float):
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

    def set_default_model(self, model:str):
        self.DEFAULT_MODEL = model

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
    def generate(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None, response_format: Optional[Dict[str, Any]] = None): pass
    @abstractmethod
    def generate_embeddings(self, content: str, model_override: Optional[str] = None): pass


class OpenAI(AiEngine, engine="openai"):
    URL = "https://api.openai.com/v1"

    def __init__(self, default_model: Optional[str] = None, embedding_model: Optional[str] = None):
        self.KEY = app.state.config.OPENAI_API_KEY
        self._default_model = default_model or AiModels.DEFAULT_OPENAI
        self._embedding_model = embedding_model or AiModels.DEFAULT_OPENAI_EMBEDDING

    def route(self, route: str = "") -> str:
        return f"{self.URL}{route}"

    def default_model(self, override: Optional[str] = None) -> str:
        return override or self._default_model

    def embeddings_model(self) -> str:
        return self._embedding_model
    def payload(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None, response_format: Optional[Dict[str, Any]] = None) -> dict:
        payload = {
            'model': self.default_model(override=model_override),  # Use 'gpt-4' if available
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            "options": {
                "temperature": self.TEMPERATURE,
                "top_k": self.TOP_K,
                "frequency_penalty": self.FREQUENCY_PENALTY,
            },
            "stream": False
        }

        if response_format:
            payload["format"] = response_format

        return payload

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

    def generate(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None, response_format: Optional[Dict[str, Any]] = None):
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
    O: ollama.Client = None

    def __init__(self, default_model: Optional[str] = None, embedding_model: Optional[str] = None):
        self.host = app.state.config.OLLAMA_HOST
        self.port = app.state.config.OLLAMA_PORT
        self._default_model = default_model or AiModels.DEFAULT_OLLAMA
        self._embedding_model = embedding_model or AiModels.DEFAULT_OLLAMA_EMBEDDING
        self.O = ollama.Client(host=app.state.config.OLLAMA_HOST)

    def parse_to_ai_response(self, o_response) -> AiResponse:
        return AiResponse.from_json(o_response.json())

    def o_generate(self, prompt:str, model_override: Optional[str] = None):
        data = self.O.generate(model=model_override if model_override else AiModels.Ollama.LLAMA3_LATEST, prompt=prompt)
        return self.parse_to_ai_response(data)

    def o_embed(self, text:str):
        data = self.O.embed(model=AiModels.Ollama.Embed.DEFAULT, input=text)
        return self.parse_to_ai_response(data)

    def o_download_model(self, model_name:str):
        yield self.O.pull(model=model_name)

    def route(self, route: str = "") -> str:
        return f"http://{self.host}:{self.port}{route}"

    def default_model(self, override: Optional[str] = None) -> str:
        return override or self._default_model

    def embeddings_model(self) -> str:
        return self._embedding_model

    def headers(self) -> Dict[str, str]:
        return {'Content-Type': 'application/json'}

    def payload(self, system_prompt: str, user_prompt: str, model_override: Optional[str] = None, response_format: Optional[Dict[str, Any]] = None):
        payload = {
            "model": self.default_model(override=model_override),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt, "images": []},
            ],
            "options": {
                "temperature": self.TEMPERATURE,
                "top_k": self.TOP_K,
                "frequency_penalty": self.FREQUENCY_PENALTY,
            },
            "stream": False
        }

        if response_format:
            payload["format"] = response_format

        return json.dumps(payload)

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

    def generate(self,
                 system_prompt: str,
                 user_prompt: str,
                 model_override: Optional[str] = None,
                 response_format: Optional[Dict[str, Any]] = None
                 ):
        payload = self.payload(system_prompt, user_prompt, model_override, response_format)
        response = requests.post(self.route("/api/chat"), headers=self.headers(), data=payload)
        if response.status_code == 200:
            response_data = response.json()
            return response_data['message']['content']
        else:
            if response: return response
            return {"error": f"Request failed with status code {response.status_code}"}
