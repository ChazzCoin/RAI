import asyncio
import datetime
import time

import aiohttp
from openai import OpenAI
import os
from dotenv import load_dotenv
from openai.types.chat import ChatCompletion
from F.LOG import Log
from F import DICT
load_dotenv()

default_model = os.getenv("DEFAULT_OPENAI_MODEL")
embedding_model = os.getenv("DEFAULT_OPENAI_EMBEDDING_MODEL")


def getClient():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_embeddings(text):
    """Asynchronously get embeddings from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
    }
    data = {
        'input': text,
        'model': 'text-embedding-ada-002',
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/embeddings', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from OpenAI API: {error}")
            response_data = await resp.json()
            embedding = response_data['data'][0]['embedding']
            return embedding

async def get_chat_completion(system_prompt, user_input):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
    }
    data = {
        'model': 'gpt-4o-mini',  # Use 'gpt-4' if available
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_input}
        ],
        'temperature': 0.7,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
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
    print('Embedding Model:', embedding_model)
    response = getClient().embeddings.create(
        input=text,
        model=embedding_model
    )
    return response.data[0].embedding


def chat_request(system: str, user: str, model: str = default_model, content_only: bool = True):
    print(f"Model: {model}")
    response = getClient().chat.completions.create(
        model=model,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
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
def chat_request_stream(system: str, user: str, model: str = default_model, content_only: bool = True):
    print(f"Model: {model}")

    # Assuming getClient().chat.completions.create is compatible with streaming
    response_stream = getClient().chat.completions.create(
        model=model,
        stream=True,  # Enable streaming
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )

    collected_response = []  # To collect and return the final content if needed

    for response_chunk in response_stream:
        # Assume response_chunk is a part of the response from the stream
        print(response_chunk)

        # Extract the content of the chunk, assuming it's in response_chunk['choices'][0]['message']['content']
        content = response_chunk.get('choices', [{}])[0].get('message', {}).get('content', "")
        if content:
            collected_response.append(content)
            yield content  # Yield the content chunk to stream it

    if content_only:
        return ''.join(collected_response)  # Return the full content if content_only is True
    return collected_response  # Return the full response chunks if not content_only


def chat_request_forward(messages: [], model: str = default_model) -> ChatCompletion:
    response = getClient().chat.completions.create(
        model=model,
        response_format={"type": "text"},
        messages=messages
    )
    return response


def get_current_timestamp():
    """Utility function to get the current timestamp in the required format."""
    return datetime.datetime.utcnow().isoformat() + 'Z'

def stream_chat_completion(system: str, user: str, model: str = "llama3:latest"):
    # Record the time before the request is sent
    start_time = time.time()

    # Send a ChatCompletion request to the OpenAI API with stream=True
    response = getClient().chat.completions.create(
        model=model,
        messages=[{'role': 'system', 'content': system},
                  {'role': 'user', 'content': user}],
        temperature=0,
        stream=True  # Enable streaming
    )

    # Create variables to collect the streamed chunks
    collected_chunks = []
    collected_messages = []

    # Iterate through the stream of events (chunks)
    for chunk in response:
        chunk_time = time.time() - start_time  # Calculate the time delay of the chunk
        collected_chunks.append(chunk)  # Save the chunk response
        chunk_message = chunk.choices[0].delta.content  # Extract the message from the chunk

        # Save the message if it exists
        if chunk_message:
            collected_messages.append(chunk_message)

        # Print the message and the time it was received after the request
        print(f"Message received {chunk_time:.2f} seconds after request: {chunk_message}")

    # Calculate the total time taken to receive the full response
    full_time = time.time() - start_time
    print(f"Full response received {full_time:.2f} seconds after request")

    # Join the collected messages into the full reply content
    full_reply_content = ''.join(collected_messages)
    print(f"Full conversation received: {full_reply_content}")

    # Return the full response content
    return full_reply_content


def stream_chat_completion2(system: str, user: str, model: str = "llama3:latest"):
    # Record the time before the request is sent
    start_time = time.time()

    # Send a ChatCompletion request to the OpenAI API with stream=True
    response = getClient().chat.completions.create(
        model=model,
        messages=[{'role': 'system', 'content': system},{'role': 'user', 'content': user}],
        temperature=0,
        stream=True  # Enable streaming
    )

    # Variables to collect the streamed chunks
    collected_messages = []
    prompt_eval_count = 0
    eval_count = 0
    prompt_eval_duration = 0  # Simulated prompt evaluation duration

    is_finished = False
    # Iterate through the stream of events (chunks)
    while not is_finished:

        for chunk in response:
            chunk_time = time.time() - start_time  # Calculate the time delay of the chunk
            timestamp = get_current_timestamp()  # Get the current timestamp

            # Extract the message content from the chunk
            choice = chunk.choices[0]

            finish_reason = DICT.get('finish_reason', choice, None)
            if finish_reason:
                if finish_reason == 'stop':
                    is_finished = True
            delta = choice.delta
            chunk_message = DICT.get('content', delta, None)
            print(chunk_message)
            if chunk_message:
                collected_messages.append(chunk_message)

                # Construct the response object for each chunk
                response_obj = {
                    "model": model,
                    "created_at": timestamp,
                    "message": {
                        "role": "assistant",
                        "content": chunk_message
                    },
                    "done": False  # Indicate that the stream is not yet done
                }

                # Yield the response object for streaming
                # print("Streaming:", response_obj)
                yield response_obj

            # Simulate evaluation counts and prompt evaluation (modify as per real implementation)
            prompt_eval_count += 1
            eval_count += 1

    # Once the stream is finished, compute the total duration
    total_duration = int((time.time() - start_time) * 1e9)  # Convert to nanoseconds
    load_duration = total_duration - prompt_eval_duration  # Simulated load duration

    # Final completion message
    final_obj = {
        "model": model,
        "created_at": get_current_timestamp(),
        "message": {
            "role": "assistant",
            "content": ''.join(collected_messages)  # Join collected messages as final content
        },
        "done_reason": "stop",
        "done": True,  # Indicate that the stream is done
        "total_duration": total_duration,
        "load_duration": load_duration,
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_duration": prompt_eval_duration,
        "eval_count": eval_count,
        "eval_duration": total_duration - prompt_eval_duration  # Simulated eval duration
    }

    # Yield the final completion message
    # print("Finished:", final_obj)
    yield final_obj


if __name__ == "__main__":
    system = "You are a knowledgeable assistant for the Park City Soccer Club, providing information about soccer programs and club activities."
    user = "What are the upcoming events?"
    # print(chat_request(system, user))
    # Example of consuming the streaming response
    # chat_request_stream_forward(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini")

    # stream_chat_completion2(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini")
    for chunk in stream_chat_completion2(system="You are an assistant", user="Hello! How are you?", model="gpt-4o-mini"):
        print(f"Streamed chunk: {chunk}")
