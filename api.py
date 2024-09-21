#!/bin/bash
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from config import env
import aiohttp
from gevent.pywsgi import WSGIServer
from quart import Quart, request, jsonify, Response
import requests
from F import DICT
from F.LOG import Log
from assistant.openai_client import get_current_timestamp, getClient, get_embeddings, truncate_text, get_chat_completion
from config.RaiModels import RAI_MODELS, MODEL_MAP
from assistant.rag import RAGWithChroma

Log = Log("RAI API Bruno Canary")


app = Quart(__name__)

# Configure OpenAI API key
default_model = "gpt-4o"
CHAT_MESSAGE_OPENAI = lambda system, user: [
      {"role": "system", "content": system },
      {"role": "user", "content": user }
    ]
ChatID = "111"

collection_name = "web_pages_2"
# rag = AsyncRagWithChroma()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

# async def rag_search(user_prompt):
#     results = await rag.query(user_prompt, n_results=5)
#     Log.i("RAG Results:", len(results))
#     system_prompt = rag.inject_into_system_prompt(results)
#     return system_prompt, results

def get_last_user_message(json_data):
    # Get the list of messages
    messages = json_data.get('messages', [])
    # Filter to find the last message with role 'user'
    last_user_message = None
    for message in reversed(messages):
        if message.get('role') == 'user':
            last_user_message = message.get('content')
            break
    return last_user_message

async def generate_chat_completion(system_prompt, user_prompt, appended_message=""):
    """Asynchronously stream chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    data = {
        'model': "gpt-4o-mini",
        'messages': [
            {'role': 'system', 'content':  system_prompt },
            {'role': 'user', 'content': user_prompt }
        ],
        'temperature': 0,
        'stream': True
    }
    start_time = time.time()
    collected_messages = []
    prompt_eval_count = 0
    eval_count = 0
    prompt_eval_duration = 0  # Simulated prompt evaluation duration

    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from OpenAI API: {error}")
            async for line in resp.content:
                chunk_time = time.time() - start_time
                timestamp = get_current_timestamp()
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                if line.startswith('data: '):
                    line = line[len('data: '):]
                if line == '[DONE]':
                    break
                try:
                    data = json.loads(line)
                    choice = data['choices'][0]
                    delta = choice.get('delta', {})
                    chunk_message = delta.get('content', None)
                    if chunk_message:
                        collected_messages.append(chunk_message)
                        response_obj = {
                            "model": "gpt-4o-mini",
                            "created_at": timestamp,
                            "message": {
                                "role": "assistant",
                                "content": chunk_message
                            },
                            "done": False  # Indicate that the stream is not yet done
                        }
                        yield f"\n{json.dumps(response_obj)}\n"
                    prompt_eval_count += 1
                    eval_count += 1
                except json.JSONDecodeError:
                    continue

    # Append any additional message at the end
    if appended_message:
        appended_obj = {
            "model": "gpt-4o-mini",
            "created_at": get_current_timestamp(),
            "message": {
                "role": "assistant",
                "content": f"\n\n {appended_message}"
            },
            "done": False  # Indicate that the stream is not yet done
        }
        yield f"\n{json.dumps(appended_obj)}\n"

@app.route('/api/chat', methods=['POST'])
async def chat_completion():
    model = "gpt-4o-mini"
    data = await request.get_data()
    jbody = json.loads(data.decode('utf-8'))
    # jbody = await request.get_data()
    user_message = get_last_user_message(jbody)
    appended_message = ""
    sys_prompt = "You are a useful assistant."
    modelIn = DICT.get('model', jbody, 'llama3:latest')

    Log.i("/api/chat", f"Model IN: {modelIn}")
    if modelIn == 'park-city:latest':
        model = MODEL_MAP[modelIn]
        embeds = await get_embeddings(user_message)
        results = await rag.query_chromadb(embeds)
        Log.i("RAG Results ASYNC:", results)
        # Extract documents from ChromaDB results
        metadatas = results.get('metadatas', [])[0]  # Get the first list of documents
        Log.i("RAG MetaDatas:", len(metadatas))
        for metadata in metadatas:
            appended_message += f"\n\nSources:\n{DICT.get('url', metadata, '')}"
        system_prompt = rag.inject_into_system_prompt(results)
        Log.i("Model Setup Finished...")

    Log.i("All Setup Finished...")
    Log.i("/api/chat", f"Model OUT: {model}")
    def generate(system_prompt, user_prompt):

        """ 1. Stream Response. """
        # Record the time before the request is sent
        start_time = time.time()
        response = getClient().chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content':  system_prompt },
                {'role': 'user', 'content': user_prompt }
            ],
            temperature=0,
            stream=True
        )
        # Variables to collect the streamed chunks
        collected_messages = []
        prompt_eval_count = 0
        eval_count = 0
        prompt_eval_duration = 0  # Simulated prompt evaluation duration
        for chunk in response:
            chunk_time = time.time() - start_time  # Calculate the time delay of the chunk
            timestamp = get_current_timestamp()  # Get the current timestamp
            choice = chunk.choices[0]
            delta = choice.delta
            chunk_message = DICT.get('content', delta, None)
            if chunk_message:
                collected_messages.append(chunk_message)
                response_obj = {
                    "model": model,
                    "created_at": timestamp,
                    "message": {
                        "role": "assistant",
                        "content": chunk_message
                    },
                    "done": False  # Indicate that the stream is not yet done
                }
                yield f"\n{json.dumps(response_obj)}\n"
            prompt_eval_count += 1
            eval_count += 1

        """ 2. Append Text/Message to end of Response. """
        if appended_message:
            appended_obj = {
                "model": model,
                "created_at": get_current_timestamp(),
                "message": {
                    "role": "assistant",
                    "content": f"\n\n {appended_message}" if appended_message else ""
                },
                "done": False  # Indicate that the stream is not yet done
            }
            yield f"\n{json.dumps(appended_obj)}\n"

        """ 3. Send Final Response. """
        # Once the stream is finished, compute the total duration
        total_duration = int((time.time() - start_time) * 1e9)  # Convert to nanoseconds
        load_duration = total_duration - prompt_eval_duration  # Simulated load duration
        final_obj = {
            "model": model,
            "created_at": get_current_timestamp(),
            "message": {
                "role": "assistant",
                "content": ''  # Join collected messages as final content
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
        yield f"\n{json.dumps(final_obj)}\n"

    async def stream(system_prompt, user_message, appended_message):
        async for chunk in generate_chat_completion(system_prompt, user_message, appended_message=appended_message):
            yield chunk
    Log.i("Responding...")
    return Response(stream(system_prompt, user_message, appended_message), content_type='text/event-stream')

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completed():
    print("Chat Completed.")
    response = {
        "model": "llama3:latest",
        "messages": [
            {
                "id": "dd6c3f37-396b-4f1e-8f67-b2105e1855a6",
                "role": "user",
                "content": "hey!",
                "timestamp": 1725999095
            },
            {
                "id": "0d018a2d-0843-4ea3-b169-ae6e68dbfaa3",
                "role": "assistant",
                "content": "Hey! It's nice to meet you. Is there something I can help you with, or would you like to chat?",
                "info": {
                    "total_duration": 5248124406,
                    "load_duration": 4317770731,
                    "prompt_eval_count": 12,
                    "prompt_eval_duration": 46358000,
                    "eval_count": 26,
                    "eval_duration": 837602000
                },
                "timestamp": 1725999095
            }
        ],
        "chat_id": ChatID
    }
    return jsonify(response), 200

@app.route('/', methods=['GET'])
async def heart():
    response = {
        "status": "available",  # or "unavailable"
        "message": "Server is running and available",
        "uptime": "24 hours",  # mock data for uptime
        "version": "1.0.0"  # mock server version
    }
    return jsonify(response), 200
@app.route('/status', methods=['GET'])
async def get_status():
    response = {
        "status": "available",  # or "unavailable"
        "message": "Server is running and available",
        "uptime": "24 hours",  # mock data for uptime
        "version": "1.0.0"  # mock server version
    }
    return jsonify(response), 200

@app.route("/api/version", methods=['GET'])
def version():
    print("version")
    return jsonify({
        "version": "0.1.45",
    }), 200

@app.route('/api/tags', methods=['GET'])
def models_api():
    print("Calling Models")
    return RAI_MODELS

@app.route('/api/tags2', methods=['GET'])
def forward_models_call_to_ollama():
    print("Calling Models")
    url = "http://192.168.1.6:11434/api/tags"
    headers = {"Content-Type": "application/json"}
    try:
        # Make a GET request to the /v1/models endpoint
        response = requests.get(url, headers=headers)
        # Check if the response is successful
        if response.status_code == 200:
            print(response.json())
            return response.json()  # Return the list of models
        else:
            return jsonify({"error": f"Failed to retrieve models, status code: {response.status_code}"})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)})

"""
    {   
    'models': [
        {'name': 'park-city:latest', 'model': 'park-city:latest', 'modified_at': '2024-07-02T06:32:47.913084094Z', 'size': 177669289, 'digest': 'c4ff0145029b23c94b81626b5cdd671a5c48140a3f8d972575efb9d145527581', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0' }}, 
        {'name': 'results-test.gguf:latest', 'model': 'results-test.gguf:latest', 'modified_at': '2024-07-02T00:04:52.581499471Z', 'size': 177669289, 'digest': '0b9252e0e7650508ae849420ac4e06678d85421355872f3d95ef1ace2059e6db', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'gpt2', 'families': ['gpt2'], 'parameter_size': '163.04M', 'quantization_level': 'Q8_0'}}, 
        {'name': 'nous-hermes2-mixtral:8x7b', 'model': 'nous-hermes2-mixtral:8x7b', 'modified_at': '2024-06-29T06:24:46.894948698Z', 'size': 26442493141, 'digest': '599da8dce2c14e54737c51f9668961bbc3526674249d3850b0875638a3e5e268', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '47B', 'quantization_level': 'Q4_0'}}, 
        {'name': 'sqlcoder:15b', 'model': 'sqlcoder:15b', 'modified_at': '2024-06-29T06:01:39.480494281Z', 'size': 8987630230, 'digest': '93bb0e8a904ff98bcc6fa5cf3b8e63dc69203772f4bc713f761c82684541d08d', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'starcoder', 'families': None, 'parameter_size': '15B', 'quantization_level': 'Q4_0'}}, 
        {'name': 'phi3:medium', 'model': 'phi3:medium', 'modified_at': '2024-06-29T06:01:39.060494165Z', 'size': 7897126241, 'digest': '1e67dff39209b792d22a20f30ebabe679c64db83de91544693c4915b57e475aa', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'phi3', 'families': ['phi3'], 'parameter_size': '14.0B', 'quantization_level': 'F16'}}, 
        {'name': 'codellama:34b', 'model': 'codellama:34b', 'modified_at': '2024-06-29T06:01:38.020493877Z', 'size': 19052049085, 'digest': '685be00e1532e01f795e04bc59c67bc292d9b1f80b5136d4fbdebe6830402132', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '34B', 'quantization_level': 'Q4_0'}}, 
        {'name': 'llava:34b', 'model': 'llava:34b', 'modified_at': '2024-06-29T06:01:38.736494074Z', 'size': 20166497526, 'digest': '3d2d24f4667475bd28d515495b0dcc03b5a951be261a0babdb82087fc11620ee', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama', 'clip'], 'parameter_size': '34B', 'quantization_level': 'Q4_0'}}, 
        {'name': 'llama3:latest', 'model': 'llama3:latest', 'modified_at': '2024-06-29T06:01:38.340493962Z', 'size': 4661224676, 'digest': '365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': ['llama'], 'parameter_size': '8.0B', 'quantization_level': 'Q4_0'}}, 
        {'name': 'codellama:13b', 'model': 'codellama:13b', 'modified_at': '2024-06-29T06:01:37.620493765Z', 'size': 7365960935, 'digest': '9f438cb9cd581fc025612d27f7c1a6669ff83a8bb0ed86c94fcf4c5440555697', 'details': {'parent_model': '', 'format': 'gguf', 'family': 'llama', 'families': None, 'parameter_size': '13B', 'quantization_level': 'Q4_0'}}
            ]
    }

"""
def bytes_to_string(byte_data: bytes, encoding: str = 'utf-8') -> str:
    if not isinstance(byte_data, bytes):
        raise ValueError("Input must be a byte string.")
    try:
        # Decode the byte string using the specified encoding
        return byte_data.decode(encoding)
    except Exception as e:
        raise ValueError(f"Decoding failed: {e}")

def inlet(user_data):
    return user_data
def outlet(user_data):
    return user_data

def __extract_ai_response_message(response):
    return response.choices[0].message.content

@app.route("/help")
def help_api():
    return "I will not help you sir."

@app.route("/heart")
def heartbeat():
    return "beat"



if __name__ == '__main__':
    port = 11434
    debug = False
    host = "0.0.0.0"
    print(f"Starting Bruno Server. Host={host}, Port={port}, Debug={debug}")
    app.run(host=host, port=port, debug=debug, loop=looper)
    app_server = WSGIServer((host, port), app)
    app_server.loop
    # app_server.serve_forever()


