import datetime
import json
import time

import aiohttp
from openai import OpenAI
import os

from openai.cli._models import BaseModel
from openai.types.chat import ChatCompletion
from F import DICT

from rai.app import state
from rai.assistant.connectors import AiModels

# default_model = os.getenv("DEFAULT_OPENAI_MODEL")
# embedding_model = os.getenv("DEFAULT_OPENAI_EMBEDDING_MODEL")
open_ai_key = os.getenv("OPENAI_API_KEY")

def getClient():
    return OpenAI(api_key=open_ai_key, timeout=10, max_retries=3)

async def get_embeddings(text):
    """Asynchronously get embeddings from OpenAI API."""
    print("GENERATE EMBEDDINGS - OPENAI")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {open_ai_key}',
    }
    data = {
        'input': text,
        'model': AiModels.DEFAULT_OPENAI_EMBEDDING,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/embeddings', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from OpenAI API: {error}")
            response_data = await resp.json()
            embedding = response_data['data'][0]['embedding']
            return embedding

async def get_chat_completion(system_prompt, user_input, model:str=None):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {open_ai_key}',
    }
    data = {
        'model': AiModels.DEFAULT_OPENAI,  # Use 'gpt-4' if available
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_input}
        ],
        'temperature': 0.7,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from OpenAI API: {error}")
            response_data = await resp.json()
            assistant_message = response_data['choices'][0]['message']['content']
            return assistant_message
def truncate_text(text, max_length):
    """Truncate text to a maximum number of characters."""
    return text[:max_length] if len(text) > max_length else text
def generate_embeddings(text):
    print('Embedding Model:', AiModels.DEFAULT_OPENAI_EMBEDDING)
    try:
        response = getClient().embeddings.create(
            input=text,
            model=AiModels.DEFAULT_OPENAI_EMBEDDING
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Failed to embed text with openai: {e}")
        return []

def openai_generate(system_prompt: str, user_prompt: str, model: str = AiModels.DEFAULT_OPENAI, content_only: bool = True):
    print(f"Model: {model}")
    response = getClient().chat.completions.create(
        model=model,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    print(response)
    if content_only:
        return response.choices[0].message.content
    return response
"""
{"model":"llama3:latest","created_at":"2024-09-16T02:10:32.443679033Z","message":{"role":"assistant","content":"?"},"done":false}
{"model":"llama3:latest","created_at":"2024-09-16T02:10:32.477253839Z","message":{"role":"assistant","content":""},"done_reason":"stop","done":true,"total_duration":4659202790,"load_duration":4270615787,"prompt_eval_count":22,"prompt_eval_duration":52448000,"eval_count":7,"eval_duration":201934000}
"""
# def chat_request_stream(system: str, user: str, model: str = AiModels.DEFAULT_OPENAI, content_only: bool = True):
#     print(f"Model: {model}")
#
#     # Assuming getClient().chat.completions.create is compatible with streaming
#     response_stream = getClient().chat.completions.create(
#         model=AiModels.DEFAULT_OPENAI,
#         stream=True,  # Enable streaming
#         response_format={"type": "text"},
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user", "content": user}
#         ]
#     )
#
#     collected_response = []  # To collect and return the final content if needed
#
#     for response_chunk in response_stream:
#         # Assume response_chunk is a part of the response from the stream
#         print(response_chunk)
#
#         # Extract the content of the chunk, assuming it's in response_chunk['choices'][0]['message']['content']
#         content = response_chunk.get('choices', [{}])[0].get('message', {}).get('content', "")
#         if content:
#             collected_response.append(content)
#             yield content  # Yield the content chunk to stream it
#
#     if content_only:
#         return ''.join(collected_response)  # Return the full content if content_only is True
#     return collected_response  # Return the full response chunks if not content_only
# def chat_request_forward(messages: [], model: str = AiModels.DEFAULT_OPENAI) -> ChatCompletion:
#     response = getClient().chat.completions.create(
#         model=model,
#         response_format={"type": "text"},
#         messages=messages
#     )
#     return response
def get_current_timestamp():
    """Utility function to get the current timestamp in the required format."""
    return datetime.datetime.utcnow().isoformat() + 'Z'


QA_SCHEMA = {
    "name": "answer_question",
    "description": "Provide a boolean answer to the given question.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question being answered."},
            "answer": {"type": "boolean", "description": "The boolean answer to the question."}
        },
        "required": ["question", "answer"]
    }
}
# async def generate_function_call(user, system, schema:dict):
#     headers = {
#         "Authorization": f"Bearer {open_ai_key}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "model": "gpt-4o-mini",  # Use the model version that supports function calling
#         "messages": [
#             {"role": "system", "content": system},
#             {"role": "user", "content": user}
#         ],
#         "functions": [
#             schema
#         ],
#         "function_call": {"name": "answer_question"}  # Explicitly invoke the function
#     }
#     async with aiohttp.ClientSession() as session:
#         async with session.post("https://api.openai.com/v1/chat/completions/chat/completions", headers=headers, json=data) as resp:
#             if resp.status != 200:
#                 error = await resp.json()
#                 raise Exception(f"Error from OpenAI API: {error}")
#             response_data = await resp.json()
#             assistant_message = response_data["choices"][0]["message"]["function_call"]["arguments"]
#             structured_data = json.loads(assistant_message)
#             # Ensure the format and return the boolean answer
#             if (
#                     isinstance(structured_data, dict) and
#                     "answer" in structured_data and
#                     isinstance(structured_data["answer"], bool)
#             ):
#                 print(structured_data["answer"])
#                 return structured_data["answer"]
#             else:
#                 print(f"Invalid response format: {structured_data}")
#                 print(assistant_message)
#                 return assistant_message

# def generate_structured_output(user_prompt:str, system_prompt:str, format:BaseModel, model_override:str=None):
#     try:
#         completion = getClient().beta.chat.completions.parse(
#             model=AiModels.DEFAULT_OPENAI if not model_override else model_override,
#             messages=[
#                 {"role": "system", "content": system_prompt },
#                 {"role": "user", "content": user_prompt }
#             ],
#             response_format=format,
#         )
#         response = completion.choices[0].message
#         # If the model refuses to respond, you will get a refusal message
#         if response.refusal:
#             print("Refused:", response.refusal)
#             return response.refusal
#         else:
#             print("Parsed:",response.parsed)
#             return response.parsed
#     except Exception as e:
#         print(e)
#         return "Uh oh. Something has gone wrong!"


"""
[
  {
    "id": "call_12345xyz",
    "type": "function",
    "function": { "name": "get_weather", "arguments": "{'location':'Paris'}" }
  }
]
"""
# def generate_tool_output(user_prompt:str, system_prompt:str, tools:[{}], model_override:str=None):
#     try:
#         completion = getClient().chat.completions.create(
#             model=AiModels.DEFAULT_OPENAI if not model_override else model_override,
#             messages=[
#                 {"role": "system", "content": system_prompt },
#                 {"role": "user", "content": user_prompt }
#             ],
#             tools=tools
#         )
#         tools_response = completion.choices[0].message.tool_calls
#         if tools_response:
#             for tool in tools_response:
#                 function_data = DICT.get("function", tool, None)
#                 if function_data:
#                     func_name = DICT.get("name", function_data, None)
#                     func_args = DICT.get("arguments", function_data, None)
#
#     except Exception as e:
#         print(e)
#         return "Uh oh. Something has gone wrong!"

if __name__ == "__main__":
    import asyncio
    system = "You are a knowledgeable assistant for the Park City Soccer Club, providing information about soccer programs and club activities."
    user = "Was George Washington ever a president?"
    # asyncio.run(generate_structured_output("how can I solve 8x + 7 = -23", MathReasoning))
    # print(chat_request(system, user))
    # Example of consuming the streaming response
    # chat_request_stream_forward(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini")

    # stream_chat_completion2(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini")
    # for chunk in stream_chat_completion2(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini"):
    #     print(f"Streamed chunk: {chunk}")
