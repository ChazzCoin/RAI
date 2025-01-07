import os
from abc import ABC, abstractmethod, abstractproperty
from typing import Optional, Dict, Type, Any
import ollama
from ollama import ChatResponse, EmbedResponse
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel

from rai import app
from rai.agents.Tools import RaiFunctionCategories, find_RaiFunction
from rai.assistant.ai_models import AiModels

open_ai_key = os.getenv("OPENAI_API_KEY")

class FusedAI(ABC):
    engines: Dict[str, Type['FusedAI']] = {}
    DEFAULT_MODEL: str = AiModels.DEFAULT_OLLAMA
    DEFAULT_EMBEDDING_MODEL: str = AiModels.DEFAULT_OLLAMA
    KEY: str = ""
    TEMPERATURE: float = 0.5
    TOP_K: int = 10
    FREQUENCY_PENALTY: float = 0.5

    O = None
    OAsync = None

    def __init_subclass__(cls, *, engine: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if not engine:
            raise ValueError("Subclasses must define an 'engine' name.")
        cls.engine = engine
        FusedAI.engines[engine] = cls
    @property
    def default_model(self) -> str:
        if self.engine == "openai":
            return AiModels.DEFAULT_OPENAI
        return AiModels.DEFAULT_OLLAMA
    @property
    def default_embedding_model(self) -> str:
        if self.engine == "openai":
            return AiModels.DEFAULT_OPENAI_EMBEDDING
        return AiModels.DEFAULT_OLLAMA_EMBEDDING

    """ SYNC """
    @abstractmethod
    def generate(self, user: str, system: str):pass
    @abstractmethod
    def generate_chat(self, messages:[{}]): pass
    @abstractmethod
    def generate_embeddings(self, content: str): pass
    @abstractmethod
    def generate_format(self, user: str, system: str, format: Type[BaseModel]): pass
    @abstractmethod
    def generate_function(self, user: str, system: str, functions: [dict]): pass
    """ ASYNC """
    @abstractmethod
    async def generate_async(self, user: str, system: str): pass
    @abstractmethod
    async def generate_chat_async(self, messages: [{}]): pass
    @abstractmethod
    async def generate_embeddings_async(self, content): pass
    @abstractmethod
    async def generate_format_async(self, user: str, system: str, format: Type[BaseModel]): pass
    @abstractmethod
    async def generate_function_async(self, user: str, system: str, functions: [dict]): pass

"""

    OPENAI ENGINE

"""
class OpenAiEngine(FusedAI, engine="openai"):
    O: OpenAI = None
    OAsync: AsyncOpenAI = None

    def __init__(self):
        self.O = OpenAI(api_key=open_ai_key, timeout=10, max_retries=3)
        self.OAsync = AsyncOpenAI(api_key=open_ai_key, timeout=10, max_retries=3)

    def generate(self, user:str, system:str):
        try:
            response = self.O.chat.completions.create(
                model=self.default_model,
                messages=[
                    { "role": "developer", "content": system },
                    { "role": "user", "content": user },
                ]
            )
            response = response.choices[0].message.content
            return response
        except Exception as e:
            print(e)
            return None
    def generate_chat(self, messages:[{}]):
        print("Generating Chat - OpenAI")
        try:
            response = self.O.chat.completions.create(
                model=self.default_model,
                messages=messages
            )
            response = response.choices[0].message.content
            # If the model refuses to respond, you will get a refusal message
            return response
        except Exception as e:
            print(e)
            return None
    def generate_embeddings(self, content: str):
        try:
            response = self.O.embeddings.create(
                input=content,
                model=self.default_embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Failed to embed text with openai: {e}")
            return []
    def generate_format(self, user: str, system: str, format: BaseModel):
        try:
            completion = self.O.beta.chat.completions.parse(
                model=self.default_model,
                messages=[
                    {"role": "developer", "content": system},
                    {"role": "user", "content": user}
                ],
                response_format=format,
            )
            response = completion.choices[0].message
            # If the model refuses to respond, you will get a refusal message
            if response.refusal:
                print("Refused:", response.refusal)
                return response.refusal
            else:
                print("Parsed:", response.parsed)
                return response.parsed
        except Exception as e:
            print(e)
            return "Uh oh. Something has gone wrong!"
    def generate_function(self, user: str, system: str, functions: [dict]):
        try:
            completion = self.O.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "developer", "content": "Which functions should I call based on the Context (Youth Soccer Club) or Topic of the Users Prompt?"},
                    {"role": "user", "content": str(user)}
                ],
                tools=functions,
            )
            response = completion.choices[0].message.tool_calls
            if response:
                tool_results = []
                for tool in response or []:
                    rai_func_def = find_RaiFunction(tool.function.name, functions)
                    tool_results.append(rai_func_def)
                return tool_results
            return None
        except Exception as e:
            print(e)
            return None
    """ ASYNC FUNCTIONS"""
    async def generate_async(self, user: str, system: str):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "developer", "content": system},
                    {"role": "user", "content": user}
                ]
            )
            response = completion.choices[0].message.content
            return response
        except Exception as e:
            print(e)
            return None
    async def generate_chat_async(self, messages: [{}]):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.default_model,
                messages=messages
            )
            response = completion.choices[0].message.content
            return response
        except Exception as e:
            print(e)
            return None
    async def generate_embeddings_async(self, content: str):
        try:
            response = await self.OAsync.embeddings.create(
                input=content,
                model=self.default_embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Failed to embed text with openai: {e}")
            return []
    async def generate_format_async(self, user: str, system: str, format: Type[BaseModel]):
        try:
            completion = await self.OAsync.beta.chat.completions.parse(
                model=self.default_model,
                messages=[
                    {"role": "developer", "content": system},
                    {"role": "user", "content": user}
                ],
                response_format=format,
            )
            response = completion.choices[0].message
            # If the model refuses to respond, you will get a refusal message
            if response.refusal:
                print("Refused:", response.refusal)
                return response.refusal
            else:
                print("Parsed:", response.parsed)
                return response.parsed
        except Exception as e:
            print(e)
            return None
    async def generate_function_async(self, user: str, system: str, functions: [dict]):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "developer", "content": system},
                    {"role": "user", "content": user}
                ],
                tools=functions,
            )
            response = completion.choices[0].message.tool_calls
            if response:
                tool_results = []
                for tool in response or []:
                    rai_func_def = find_RaiFunction(tool.function.name, functions)
                    tool_results.append(rai_func_def)
                return tool_results
            return None
        except Exception as e:
            print(e)
            return None
"""

    OLLAMA ENGINE

"""
class OllamaEngine(FusedAI, engine="ollama"):
    O: ollama.Client = None
    OAsync: ollama.AsyncClient = None

    def __init__(self):
        self.O = ollama.Client(host=app.state.config.OLLAMA_HOST)
        self.OAsync = ollama.AsyncClient(host=app.state.config.OLLAMA_HOST)

    def download_ollama_model(self, model_name: str):
        yield self.O.pull(model=model_name)

    """ SYNC """
    def generate(self, user: str, system: str):
        print("Generating Async Chat - Ollama")
        try:
            data: ChatResponse = self.O.generate(
                model=self.default_model,
                prompt=user,
                system=system
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    def generate_chat(self, messages:[{}]):
        print("Generating Async Chat - Ollama")
        try:
            data: ChatResponse = self.O.chat(
                model=self.default_model,
                messages=messages
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    def generate_embeddings(self, content: str):
        try:
            data: EmbedResponse = self.O.embed(
                model=self.default_embedding_model,
                input=content
            )
            return data.embeddings
        except Exception as e:
            print(e)
            return None
    def generate_format(self, user:str, system:str, format: BaseModel):
        try:
            data: ChatResponse = self.O.chat(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user, "images": []},
                ],
                format=format.model_json_schema()
            )
            answer = format.model_validate_json(data.message.content)
            return answer
        except Exception as e:
            print(e)
            return None
    def generate_function(self, user:str, system:str, functions: [dict]):
        try:
            data: ChatResponse = self.O.chat(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user, "images": []},
                ],
                tools=functions
            )
            tool_results = []
            for tool in data.message.tool_calls or []:
                rai_func_def = find_RaiFunction(tool.function.name, functions)
                tool_results.append(rai_func_def)
            return tool_results
        except Exception as e:
            print(e)
            return None
    """ ASYNC """
    async def generate_chat_async(self, messages: [{}]):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_model,
                messages=messages
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    async def generate_async(self, user:str, system:str):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user, "images": []},
                ]
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    async def generate_embeddings_async(self, content):
        try:
            data: EmbedResponse = await self.OAsync.embed(
                model=self.default_embedding_model,
                input=content
            )
            return data.embeddings
        except Exception as e:
            print(e)
            return None
    async def generate_format_async(self, user:str, system:str, format: BaseModel):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user, "images": []},
                ],
                format=format.model_json_schema()
            )
            answer = format.model_validate_json(data.message.content)
            return answer
        except Exception as e:
            print(e)
            return None
    async def generate_function_async(self, user:str, system:str, functions: [dict]):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_model,
                messages=[
                    { "role": "system", "content": system },
                    { "role": "user", "content": user, "images": [] },
                ],
                tools=functions
            )
            tool_results = []
            for tool in data.message.tool_calls or []:
                rai_func_def = find_RaiFunction(tool.function.name, functions)
                tool_results.append(rai_func_def)
            return tool_results
        except Exception as e:
            print(e)
            return None





