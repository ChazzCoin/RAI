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
from config.RaiModels import RAI_MODELS, getMappedModel, getMappedCollection, getMappedPrompt
from chdb.rag import RAGWithChroma
from config.redisdb import RedisClient
from assistant.context import ContextHelper

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)

collection_name = "web_pages_2"
contexter = ContextHelper()
cache = RedisClient()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

RAI_VERSION = "0.1.1"

@app.route('/api/chat', methods=['POST'])
async def chat_completion():
    model = "gpt-4o-mini"
    data = await request.get_data()
    jbody = json.loads(data.decode('utf-8'))
    messages = jbody.get('messages', [])

    # chatId = DICT.get('chatId', data, False)
    # print(chatId)

    modelIn = DICT.get('model', jbody, model)
    model = getMappedModel(modelIn)
    cache_queue = cache.get_queued_chat_data(model)
    print(cache_queue)
    Log.i("/api/chat", f"Model IN: {modelIn}")
    Log.i("/api/chat", f"Model OUT: {model}")

    user_message = get_last_user_message(jbody)
    """     USER PROMPT INTERCEPTOR    """
    user_prompt = await interceptUserPrompt(modelIn=modelIn, user_message=user_message)
    print("--User Prompt--")
    print(user_prompt)
    new_user_message = { 'role': 'user', 'content': user_prompt }
    messages = jbody.get('messages', [])
    if len(messages) <= 1:
        Log.i("Creating New Message...")
        new_system_prompt = getMappedPrompt(modelIn=modelIn)
        temp = [
            { 'role': 'system', 'content': new_system_prompt },
            LIST.get(0, messages, new_user_message)
        ]
        messages = temp
    else:
        Log.i("Appending New Message...")
        messages.append(new_user_message)
    """     GENERATE AI CHAT RESPONSE   """
    ai_response = await get_chat_completion(messages)
    print("--AI Response--")
    print(ai_response)

    # cache.queue_chat_data(model, system_prompt)
    appended_message = f"""
    \n\nRAI Youth Sports Chat\nAI Model: {model}\nRai Version: {RAI_VERSION}
    """
    appended_response = appender(response_message=ai_response, message_to_append=appended_message)
    final_response = to_chat_response(appended_response, role="assistant")
    return Response(f"\n{json.dumps(final_response)}\n", content_type='text/event-stream')

"""     
CHROMADB SEARCH     
"""
async def search(user_message:str, collection_name:str):
    embeds = await get_embeddings(user_message)
    results = await rag.query_chromadb(embeds, collection_name)
    Log.i("Search Result Count:", results)
    return results
"""     
USER PROMPT INTERCEPTOR   
"""
async def interceptUserPrompt(modelIn, user_message:str):
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
    return rag.inject_into_system_prompt(user_message, docs=results)
"""     
RESPONSE MESSAGE APPENDER   
"""
def appender(response_message="", metadatas:[]=None, message_to_append:str=None):
    if message_to_append:
        response_message += message_to_append
    if metadatas:
        for metadata in metadatas:
            response_message += f"\n\nSources:\n{DICT.get('url', metadata, '')}"
    return response_message
""" HELPER """
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
""" HELPER """
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
""" 
GENERATE AI CHAT RESPONSE 
"""
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

"""
    -> API HEALTH CHECKS AND SUCH
"""
@app.route('/image/remarkable')
def get_image():
    # Assuming the images are stored in the 'images' directory
    file_path = f'{IMAGE_FOLDER}/suspended.png'
    try:
        return send_file(file_path, mimetype='image/png')
    except FileNotFoundError:
        return {"error": "File not found"}, 404

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