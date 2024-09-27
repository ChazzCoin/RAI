#!/bin/bash
import asyncio
import json
import os.path
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from config import env
import aiohttp
from quart import Quart, request, jsonify, Response, send_file
import requests
from F import DICT, LIST
from F.LOG import Log
from assistant.openai_client import get_current_timestamp, get_embeddings
from config.RaiModels import RAI_MODELS, getMappedModel, getMappedCollection
from chdb.rag import RAGWithChroma
from config.redisdb import RedisClient

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)

collection_name = "web_pages_2"
cache = RedisClient()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

@app.route('/image/remarkable')
def get_image():
    # Assuming the images are stored in the 'images' directory
    file_path = f'{IMAGE_FOLDER}/suspended.png'
    try:
        return send_file(file_path, mimetype='image/png')
    except FileNotFoundError:
        return {"error": "File not found"}, 404

@app.route('/api/chat', methods=['POST'])
async def chat_completion():
    model = "gpt-4o-mini"
    data = await request.get_data()
    jbody = json.loads(data.decode('utf-8'))
    messages = jbody.get('messages', [])

    modelIn = DICT.get('model', jbody, model)
    model = getMappedModel(modelIn)
    cache_queue = cache.get_queued_chat_data(model)
    print(cache_queue)
    Log.i("/api/chat", f"Model IN: {modelIn}")
    Log.i("/api/chat", f"Model OUT: {model}")

    """ CHROMADB SEARCH """
    async def search(user_message:str, collection_name:str):
        embeds = await get_embeddings(user_message)
        results = await rag.query_chromadb(embeds, collection_name)
        Log.i("Search Result Count:", results)
        return results

    """ RESPONSE MESSAGE APPENDER """
    def appender(response_message="", metadatas:[]=None, message_to_append:str=None):
        if message_to_append:
            response_message += message_to_append
        if metadatas:
            for metadata in metadatas:
                response_message += f"\n\nSources:\n{DICT.get('url', metadata, '')}"
        return response_message

    """ SYSTEM PROMPT INTERCEPTOR """
    async def interceptUserPrompt(user_message:str):
        if str(modelIn) == "park-city:web":
            Log.i("Park-City Flow", modelIn)
            collection = getMappedCollection(modelIn)
            Log.i("Using Park-City Collection", collection)
            results = await search(user_message, collection)
        elif modelIn == 'ChromaDB:search':
            collection_name = extract_args(user_message, 1)
            results = await search(user_message, collection_name)
        else:
            Log.i("Returning Generic SYS Prompt")
            return "You are a useful assistant."
        Log.i("Returning custom SYS Prompt.")
        # await asyncio.sleep(1)
        return rag.inject_into_system_prompt(user_message, docs=results)

    """ STREAM FINAL AI CHAT RESPONSE """
    async def stream(sp, user_message, appended_message, messages):
        async for chunk in generate_chat_completion(sp, user_message, appended_message=appended_message, messages=messages):
            yield chunk

    user_message = get_last_user_message(jbody)
    user_prompt = await interceptUserPrompt(user_message)
    new_user_message = { 'role': 'user', 'content': user_prompt }
    messages = jbody.get('messages', [])
    if len(messages) <= 1:
        Log.i("Creating New Message...")
        new_system_prompt = """
        
        Your name is Park City Rep and you are here to serve at the pleasure of the members of the soccer club, Park City Soccer Club.
        
        You are going to be a detailed and honest customer service representative who will answer questions based on information given to you.
        You specialize in understanding youth soccer clubs, organizational structure, youth soccer parents, youth soccer coaches, youth soccer players.
        If you do not know the answer based on information I give you, please just state you don't know.
        """
        temp = [
            { 'role': 'system', 'content': new_system_prompt },
            LIST.get(0, messages, new_user_message)
        ]
        messages = temp
    else:
        Log.i("Appending New Message...")
        messages.append(new_user_message)

    ai_response = await get_chat_completion(messages)

    # cache.queue_chat_data(model, system_prompt)
    appended_message = f"""
    \n\nRAI Youth Sports Chat: {model}
    """
    appended_response = appender(response_message=ai_response, message_to_append=appended_message)
    final_response = to_chat_response(appended_response, role="assistant")
    return Response(f"\n{json.dumps(final_response)}\n", content_type='text/event-stream')

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

def to_chat_response(message:str, role:str="user", model:str="gpt-4o-mini", isDone:bool=False):
    return {
        "model": model,
        "created_at": get_current_timestamp(),
        "message": {
            "role": role,
            "content": message
        },
        "done": isDone  # Indicate that the stream is not yet done
    }

async def get_chat_completion(messages:[]):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    data = {
        'model': "gpt-4o-mini",
        'messages': messages,
        'temperature': 0,
        'stream': False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from OpenAI API: {error}")
            response_data = await resp.json()
            assistant_message = response_data['choices'][0]['message']['content']
            return assistant_message

async def generate_chat_completion(system_prompt, user_prompt, appended_message="", messages:[]=None):
    """Asynchronously stream chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    if not messages:
        messages = [
                {'role': 'system', 'content':  system_prompt },
                {'role': 'user', 'content': user_prompt }
            ]
    data = {
        'model': "gpt-4o-mini",
        'messages': messages,
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