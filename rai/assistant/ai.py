import json
import requests
from rai import app
from abc import ABC, abstractmethod
from typing import Dict, Type, Any
import ollama
from typing import List, Optional

class AiResponse:
    def __init__(self, model: str, created_at: Optional[str], done: Optional[bool], done_reason: Optional[str],
                 total_duration: int, load_duration: int, prompt_eval_count: int,
                 prompt_eval_duration: Optional[int], eval_count: Optional[int], eval_duration: Optional[int],
                 embeddings: List[List[float]], response: str):
        self.model = model
        self.created_at = created_at
        self.done = done
        self.done_reason = done_reason
        self.total_duration = total_duration
        self.load_duration = load_duration
        self.prompt_eval_count = prompt_eval_count
        self.prompt_eval_duration = prompt_eval_duration
        self.eval_count = eval_count
        self.eval_duration = eval_duration
        self.embeddings = embeddings
        self.response = response

    def get_response(self):
        if self.response: return self.response
        if self.embeddings: return self.embeddings

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(
            model=data.get('model', None),
            created_at=data.get('created_at', None),
            done=data.get('done', None),
            done_reason=data.get('done_reason', None),
            total_duration=data.get('total_duration', None),
            load_duration=data.get('load_duration', None),
            prompt_eval_count=data.get('prompt_eval_count', None),
            prompt_eval_duration=data.get('prompt_eval_duration', None),
            eval_count=data.get('eval_count', None),
            eval_duration=data.get('eval_duration', None),
            embeddings=data.get('embeddings', None),
            response=data.get('response', None)
        )

class AiModels:
    DEFAULT_OPENAI_EMBEDDING = "text-embedding-3-large"
    DEFAULT_OLLAMA_EMBEDDING = "nomic-embed-text"
    DEFAULT_OPENAI = "gpt-4o-mini"
    DEFAULT_OLLAMA = "llama3.2"

    class OpenAi:
        # GPT-4 Series
        GPT4o = "gpt-4o"
        GPT4oMini = "gpt-4o-mini"
        GPT4_TURBO = "gpt-4-turbo"  # More capable with a 128k context window and cost efficiency :contentReference[oaicite:0]{index=0}
        GPT4_8K = "gpt-4-8k"        # Supports up to 8,192 tokens
        GPT4_32K = "gpt-4-32k"      # Supports up to 32,768 tokens :contentReference[oaicite:1]{index=1}
        # GPT-3.5 Series
        GPT3_5_TURBO = "gpt-3.5-turbo"
        GPT3_5_TURBO_16K = "gpt-3.5-turbo-16k"  # Extended context window
        # o1 Series
        O1_PREVIEW = "o1-preview"   # Enhanced reasoning abilities :contentReference[oaicite:2]{index=2}
        O1_MINI = "o1-mini"         # Lightweight version of o1

        class Embed:
            DEFAULT = "text-embedding-ada-002"
            TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"  # Smaller, efficient model
            TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"  # Larger, more powerful model

    class Ollama:
        # Llama Series
        LLAMA3_LATEST = "llama3:latest"
        LLAMA3_2 = "llama3.2"
        LLAMA3_3 = "llama3.3"       # Latest version :contentReference[oaicite:3]{index=3}
        # Phi Series
        PHI3 = "phi3"               # Available model :contentReference[oaicite:4]{index=4}
        # Mistral Series
        MISTRAL = "mistral"         # Available model :contentReference[oaicite:5]{index=5}
        # Gemma Series
        GEMMA2 = "gemma2"           # Available model :contentReference[oaicite:6]{index=6}
        GEMMA7B = "gemma:7b"        # 7B parameter model :contentReference[oaicite:7]{index=7}
        # Qwen2 Math Series
        QWEN2_MATH = "qwen2-math"   # Specialized math language model :contentReference[oaicite:8]{index=8}

        class Embed:
            DEFAULT = "nomic-embed-text"
            MXBAI_EMBED_LARGE = "mxbai-embed-large"  # Versatile model with 334M parameters
            ALL_MINILM = "all-minilm"  # Compact model with 22M parameters


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


