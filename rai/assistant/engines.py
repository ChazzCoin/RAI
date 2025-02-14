import base64
import mimetypes
import os
from abc import ABC, abstractmethod, abstractproperty
from typing import Optional, Dict, Type, Any, List
import ollama
from ollama import ChatResponse, EmbedResponse
from openai import OpenAI, AsyncOpenAI, Audio
from pydantic import BaseModel
from rai import app
from rai.agents.Tools import find_RaiFunction
from rai.assistant.ai_models import AiModels

import math
import tempfile
from pydub import AudioSegment


def get_image_data_url(image_input, mime_type=None):

    # Step 1: Determine and read the image bytes
    try:
        if isinstance(image_input, bytes):
            image_bytes = image_input
            # If MIME type wasn't provided, default to JPEG for raw bytes
            if mime_type is None:
                mime_type = 'image/jpeg'
        elif isinstance(image_input, str):
            # Assume a file path; verify it exists
            if not os.path.isfile(image_input):
                raise FileNotFoundError(f"File not found: {image_input}")
            with open(image_input, 'rb') as file_obj:
                image_bytes = file_obj.read()
            # If MIME type wasn't provided, try to infer from the file extension
            if mime_type is None:
                mime_type, _ = mimetypes.guess_type(image_input)
                if mime_type is None:
                    mime_type = 'image/jpeg'  # Fallback default
        elif hasattr(image_input, 'read'):
            # File-like object; read its bytes
            image_bytes = image_input.read()
            # If MIME type wasn't provided, default to JPEG
            if mime_type is None:
                mime_type = 'image/jpeg'
        else:
            raise TypeError("Invalid image input type. Must be bytes, a file path, or a file-like object.")
    except Exception as e:
        print(f"Error reading image input: {e}")
        return None

    # Step 2: Base64 encode the image bytes
    try:
        base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        print(f"Error encoding image bytes to Base64: {e}")
        return None

    # Step 3: Construct the data URL
    data_url = f"data:{mime_type};base64,{base64_encoded}"
    return data_url


class FusedResult(BaseModel):
    success: bool
    message: str
    images: List[Any]
    function: str
    format: Optional[Any]


open_ai_key = os.getenv("OPENAI_API_KEY")
class FusedAI(ABC):
    engines: Dict[str, Type['FusedAI']] = {}
    MODEL_OVERRIDE = None
    DEFAULT_MODEL: str = AiModels.DEFAULT_OLLAMA
    DEFAULT_EMBEDDING_MODEL: str = AiModels.DEFAULT_OLLAMA
    DEFAULT_FUNCTION_MODEL: str = AiModels.DEFAULT_OLLAMA
    DEFAULT_FORMAT_MODEL: str = AiModels.DEFAULT_OLLAMA
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
    # @property
    # def default_model(self) -> str:
    #     if self.engine == "openai":
    #         return AiModels.DEFAULT_OPENAI
    #     return AiModels.DEFAULT_OLLAMA
    @property
    def default_embedding_model(self) -> str:
        if self.engine == "openai":
            return AiModels.DEFAULT_OPENAI_EMBEDDING
        return AiModels.DEFAULT_OLLAMA_EMBEDDING
    @property
    def default_function_model(self) -> str:
        if self.engine == "openai":
            return AiModels.DEFAULT_OPENAI_FUNCTION
        return AiModels.DEFAULT_OLLAMA_FUNCTION
    @property
    def default_format_model(self) -> str:
        if self.engine == "openai":
            return AiModels.DEFAULT_OPENAI_FORMAT
        return AiModels.DEFAULT_OLLAMA_FORMAT

    @abstractmethod
    def engine_model(self) -> str: pass
    """ SYNC """
    @abstractmethod
    def generate(self, user: str, system: str, image=None):pass
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
{
    "type": "image_url",
    "image_url": {
        "url": "",
    },
},
"""
MESSAGE_SYSTEM = lambda system: { "role": "developer", "content": str(system) }
MESSAGE_USER = lambda user: { "role": "user", "content": str(user) }
MESSAGE_IMAGE = lambda user, img: {
    "role": "user",
    "content": [
        {"type": "text", "text": user},
        {
            "type": "image_url",
            "image_url": {
                "url": get_image_data_url(img),
            }
        },
    ],
}

def buildMessage(user:str, system:str, image=None) -> Any:
    if image is None:
        return [
            MESSAGE_SYSTEM(system),
            MESSAGE_USER(user),
        ]
    return [
        MESSAGE_IMAGE(user, image)
    ]

class OpenAiEngine(FusedAI, engine="openai"):
    O: OpenAI = None
    OAsync: AsyncOpenAI = None

    def __init__(self):
        self.O = OpenAI(api_key=open_ai_key, timeout=20, max_retries=3)
        self.OAsync = AsyncOpenAI(api_key=open_ai_key, timeout=20, max_retries=3)

    def engine_model(self):
        if self.MODEL_OVERRIDE: return self.MODEL_OVERRIDE
        return AiModels.DEFAULT_OPENAI

    def generate(self, user:str, system:str, image=None):
        try:
            response = self.O.chat.completions.create(
                model=self.engine_model(),
                messages=buildMessage(user, system, image)
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
                model=self.engine_model(),
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
    def generate_format(self, user: str, system: str, format: BaseModel, image=None):
        try:
            completion = self.O.beta.chat.completions.parse(
                model=self.default_format_model,
                messages=buildMessage(user, system, image),
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
            return f"Uh oh. Something has gone wrong!: {e}"
    def generate_function(self, user: str, system: str, functions: [dict], image=None):
        try:
            completion = self.O.chat.completions.create(
                model=self.default_function_model,
                messages=buildMessage(user, system, image),
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
    async def generate_async(self, user: str, system: str, image=None):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.engine_model(),
                messages=buildMessage(user, system, image),
            )
            response = completion.choices[0].message.content
            return response
        except Exception as e:
            print(e)
            return None
    async def generate_chat_async(self, messages: [{}], image=None):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.engine_model(),
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
    async def generate_format_async(self, user: str, system: str, format: Type[BaseModel], image=None):
        try:
            completion = await self.OAsync.beta.chat.completions.parse(
                model=self.default_format_model,
                messages=buildMessage(user, system, image),
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
    async def generate_function_async(self, user: str, system: str, functions: [dict], image=None):
        try:
            completion = await self.OAsync.chat.completions.create(
                model=self.default_function_model,
                messages=buildMessage(user, system, image),
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

    def engine_model(self):
        if self.MODEL_OVERRIDE: return self.MODEL_OVERRIDE
        return AiModels.DEFAULT_OLLAMA

    def download_ollama_model(self, model_name: str):
        yield self.O.pull(model=model_name)

    """ SYNC """
    def generate(self, user: str, system: str, image=None):
        print("Generating Async Chat - Ollama")
        try:
            data: ChatResponse = self.O.generate(
                model=self.engine_model(),
                prompt=user,
                system=system
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    def generate_chat(self, messages:[{}], image=None):
        print("Generating Async Chat - Ollama")
        try:
            data: ChatResponse = self.O.chat(
                model=self.engine_model(),
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
    def generate_format(self, user:str, system:str, format: BaseModel, image=None):
        try:
            data: ChatResponse = self.O.chat(
                model=self.engine_model(),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user },
                ],
                format=format.model_json_schema()
            )
            answer = format.model_validate_json(data.message.content)
            return answer
        except Exception as e:
            print(e)
            return None
    def generate_function(self, user:str, system:str, functions: [dict], image=None):
        try:
            data: ChatResponse = self.O.chat(
                model=self.default_function_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user },
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
                model=self.engine_model(),
                messages=messages
            )
            return data.message.content
        except Exception as e:
            print(e)
            return None
    async def generate_async(self, user:str, system:str, image=None):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.engine_model(),
                messages=[
                    {"role": "system", "content": system },
                    {"role": "user", "content": user },
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
    async def generate_format_async(self, user:str, system:str, format: BaseModel, image=None):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_format_model,
                messages=[
                    { "role": "system", "content": system },
                    { "role": "user", "content": user },
                ],
                format=format.model_json_schema()
            )
            answer = format.model_validate_json(data.message.content)
            return answer
        except Exception as e:
            print(e)
            return None
    async def generate_function_async(self, user:str, system:str, functions: [dict], image=None):
        try:
            data: ChatResponse = await self.OAsync.chat(
                model=self.default_function_model,
                messages=[
                    { "role": "system", "content": system },
                    { "role": "user", "content": user },
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





def transcribe_audio_to_file(audio_path, output_path="transcript.txt", chunk_length_ms=5*60*1000):
    """
    Transcribes an audio file by splitting it into smaller chunks, transcribing each chunk using OpenAI's Whisper API,
    and combining the results into a single text file.

    Parameters:
    - audio_path (str): Path to the input audio file.
    - output_path (str): Path to save the final transcript. Defaults to "transcript.txt".
    - chunk_length_ms (int): Length of each chunk in milliseconds. Defaults to 5 minutes.
    """
    # Ensure the OpenAI API key is set
    O = OpenAI(api_key=open_ai_key, timeout=20, max_retries=3)
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)
    total_length_ms = len(audio)
    print(f"Total audio length: {total_length_ms / 1000:.2f} seconds.")

    # Calculate the number of chunks needed
    num_chunks = math.ceil(total_length_ms / chunk_length_ms)
    print(f"Splitting audio into {num_chunks} chunks of up to {chunk_length_ms / 1000 / 60:.2f} minutes each.")

    transcripts = []

    for i in range(num_chunks):
        start_ms = i * chunk_length_ms
        end_ms = min((i + 1) * chunk_length_ms, total_length_ms)
        chunk = audio[start_ms:end_ms]

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            chunk.export(temp_audio_file.name, format="mp3")
            temp_audio_path = temp_audio_file.name

        print(f"Processing chunk {i+1}/{num_chunks}: {start_ms/1000:.2f}s to {end_ms/1000:.2f}s")

        try:
            with open(temp_audio_path, "rb") as audio_file:
                response =  O.audio.transcriptions.with_raw_response.create(
                    file=audio_file,
                    model="whisper-1",
                    response_format="text"  # Other options: "json", "srt", "verbose_json"
                )
                transcript = response.content
                if isinstance(transcript, bytes):
                    transcript = transcript.decode('utf-8')
                elif not isinstance(transcript, str):
                    # If transcript is neither bytes nor str, convert it to str
                    transcript = str(transcript)
                transcripts.append(transcript)
        except Exception as e:
            print(f"Error transcribing chunk {i+1}: {e}")
            transcripts.append(f"[Error transcribing chunk {i+1}]")
        finally:
            # Clean up the temporary file
            os.remove(temp_audio_path)

    # Combine all transcripts into a single text
    full_transcript = "\n".join(transcripts)

    # Save the combined transcript to the output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    print(f"Transcription completed. Full transcript saved to {output_path}")

    return full_transcript




if __name__ == '__main__':
    print(transcribe_audio_to_file("/Users/chazzromeo/Downloads/section_2.mp4", "/Users/chazzromeo/Documents/section_2.txt"))
