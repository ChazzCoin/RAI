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
from F import DICT, LIST
from F.LOG import Log
from assistant.openai_client import get_current_timestamp, get_embeddings
from config.RaiModels import RAI_MODELS, getMappedModel, getMappedCollection
from assistant.rag import RAGWithChroma

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)

# Configure OpenAI API key
# default_model = "gpt-4o"
# CHAT_MESSAGE_OPENAI = lambda system, user: [
#       {"role": "system", "content": system },
#       {"role": "user", "content": user }
#     ]
# ChatID = "111"

collection_name = "web_pages_2"
# rag = AsyncRagWithChroma()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

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

    modelIn = DICT.get('model', jbody, model)
    model = getMappedModel(modelIn)
    Log.i("/api/chat", f"Model IN: {modelIn}")
    Log.i("/api/chat", f"Model OUT: {model}")

    async def search(user_message:str, collection_name:str):
        embeds = await get_embeddings(user_message)
        results = await rag.query_chromadb(embeds, collection_name)
        Log.i("Search Result Count:", results)
        return results
    def appender(appended_message="", metadatas:[]=None, message:str=None):
        if message:
            appended_message += message
        if metadatas:
            for metadata in metadatas:
                appended_message += f"\n\nSources:\n{DICT.get('url', metadata, '')}"
        return appended_message

    async def interceptSystemPrompt(user_message:str):
        if modelIn == 'park-city:latest' or modelIn == 'park-city:gpt4o':
            results = await search(user_message, getMappedCollection(modelIn))
        elif modelIn == 'ChromaDB:search':
            collection_name = extract_args(user_message, 1)
            results = await search(user_message, collection_name)
        else:
            Log.i("Returning Generic SYS Prompt")
            return "You are a useful assistant."
        syspromp = rag.inject_into_system_prompt(docs=results)
        Log.i("Returning custom SYS Prompt.", results)
        return syspromp

    user_message = get_last_user_message(jbody)
    appended_message = appender(message=f"Model Used: {model}")
    system_prompt = await interceptSystemPrompt(user_message)
    print(system_prompt)
    async def stream(system_prompt, user_message, appended_message):
        async for chunk in generate_chat_completion(system_prompt, user_message, appended_message=appended_message):
            yield chunk
    return Response(stream(system_prompt, user_message, appended_message), content_type='text/event-stream')

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

@app.route("/help")
def help_api():
    return "I will not help you sir."

@app.route("/heart")
def heartbeat():
    return "beat"

def extract_args(input_string, word_count):
    """Extract the first 'word_count' words from the input string."""
    # Split the string into words
    words = input_string.split()
    # Return the first 'word_count' words
    args = words[:word_count]
    Log.i(f"Args: {args}")
    return str(LIST.get(0, args, "")).strip()


if __name__ == '__main__':
    port = 11434
    debug = False
    host = "0.0.0.0"
    print(f"Starting Bruno Server. Host={host}, Port={port}, Debug={debug}")
    app.run(host=host, port=port, debug=debug, loop=looper)