#!/bin/bash
import asyncio
import json
import os.path
from concurrent.futures import ThreadPoolExecutor
from config import env
import aiohttp
from quart import Quart, request, jsonify, Response, send_file
import requests
from F import DICT, LIST
from F.LOG import Log
from assistant.openai_client import get_current_timestamp, get_embeddings
from config.RaiModels import RAI_MODELS, RAI_MODs
from chdb.rag import RAGWithChroma
from config.redisdb import RedisClient
from assistant.context import ContextHelper

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)

collection_name = "documents"
contexter = ContextHelper()
cache = RedisClient()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

RAI_VERSION = "0.3.0:hypercorn"
RAI_FOOTER_MESSAGE = lambda model, text: f"""\n
{text}\n
| Rai Youth Sports Chat | AI Model: {model} | API Version: {RAI_VERSION} |
"""

@app.route('/api/chat', methods=['POST'])
async def chat_completion():

    """     PARSE REQUEST IN    """
    data = await request.get_data()
    jbody = json.loads(data.decode('utf-8'))
    messages = jbody.get('messages', [])

    # chatId = DICT.get('chatId', request, False)
    # print(chatId)

    """     GET MAPPED MODEL      """
    request_in_model = DICT.get('model', jbody, 'gpt-4o-mini')
    modelIn_data = DICT.get(request_in_model, RAI_MODs)

    mod_title = DICT.get('title', modelIn_data)
    mod_ai_name = DICT.get('ai_name', modelIn_data)
    mod_org_rep_type = DICT.get('org_rep_type', modelIn_data)
    mod_collection = DICT.get('collection', modelIn_data)
    # zip = DICT.get('zip', modelIn_data, '00000')
    mod_specialty = DICT.get('org_specialty', modelIn_data)
    mod_system_prompt_lambda = DICT.get('prompt', modelIn_data)(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
    mod_context_prompt_lambda = DICT.get('context_prompt', modelIn_data)
    mod_openai_model = DICT.get('openai', modelIn_data, 'gpt-4o-mini')
    mod_ollama_model = DICT.get('ollama', modelIn_data, 'llama3:latest')

    """ TODO     CACHE OUT    """
    # cache_queue = cache.get_queued_chat_data(modelIn)

    """     USER PROMPT INTERCEPTOR    """
    user_message = get_last_user_message(jbody)
    pre_user_messages = get_previous_user_messages(jbody)
    ollama_prompt = mod_context_prompt_lambda(pre_user_messages)

    ollama_request = await ollama_quick_generation(ollama_prompt, user_message, modelIn=mod_ollama_model)
    print(ollama_request)
    final_user_prompt = f"{user_message}\n{ollama_request}"
    user_prompt = await interceptUserPrompt(collection=mod_collection, user_message=final_user_prompt, debug=True)
    new_user_message = { 'role': 'user', 'content': user_prompt }

    """     SETUP MESSAGES FOR CHAT SEQUENCE   """
    messages = setupMessagesForChatSequence(mod_system_prompt_lambda, messages, new_user_message)

    """     GENERATE AI CHAT RESPONSE   """
    ai_response = await openai_chat_generation(messages, modelIn=mod_openai_model, debug=True)

    """ TODO    CACHE IN    """
    # cache.queue_chat_data(modelIn, ai_response)

    """     FOOTER MESSAGE     """
    appended_message = RAI_FOOTER_MESSAGE(mod_openai_model, "")

    """     PREPARE AND SEND FINAL RESPONSE     """
    appended_response = appender(response_message=ai_response, message_to_append=appended_message)
    final_response = to_chat_response(appended_response, role="assistant")
    return Response(f"\n{json.dumps(final_response)}\n", content_type='text/event-stream')


""" 
CACHE WEATHER
"""
def cache_weather(zip):
    from agents.weather import get_weather_by_zip
    weather_cache = cache.get_data(f"weather:{zip}")
    if weather_cache:
        return weather_cache
    weather_result = get_weather_by_zip(zip)
    cache.add_data(f"weather:{zip}", data=weather_result, ttl=50000)
    return weather_result

""" 
GENERATE AI CHAT RESPONSE 
"""
async def openai_chat_generation(messages:[], modelIn:str="gpt-4o-mini", debug:bool=False):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    data = {
        'model': modelIn,
        'messages': messages,
        'temperature': 0,
        'stream': False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from Open AI: {error}")
            response_data = await resp.json()
            assistant_message = response_data['choices'][0]['message']['content']
            if debug:
                print("--AI Response--")
                print(assistant_message)
            return assistant_message
async def ollama_chat_generation(messages:[], debug:bool=False):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    data = {
        'model': "llama3:latest",
        'messages': messages,
        'temperature': 0,
        'stream': False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('http://192.168.1.6:11434/api/chat', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from Ollama AI: {error}")
            response_data = await resp.json()
            assistant_message = response_data['message']['content']
            if debug:
                print("--AI Response--")
                print(assistant_message)
            return assistant_message
async def ollama_quick_generation(system_prompt, user_prompt, modelIn:str="llama3:latest", debug:bool=False):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env("OPENAI_API_KEY")}',
    }
    data = {
        'model': modelIn,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_prompt }
        ],
        'temperature': 0,
        'stream': False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('http://192.168.1.6:11434/api/chat', headers=headers, json=data) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from Ollama AI: {error}")
            response_data = await resp.json()
            assistant_message = response_data['message']['content']
            if debug:
                print("--AI Response--")
                print(assistant_message)
            return assistant_message
"""     
SETUP MESSAGES FOR CHAT SEQUENCE   
"""
def setupMessagesForChatSequence(system_prompt, messages, new_user_message):
    if len(messages) <= 1:
        Log.i("Creating New Message...")
        temp = [
            {'role': 'system', 'content': system_prompt},
            LIST.get(0, messages, new_user_message)
        ]
        messages = temp
    else:
        Log.i("Appending New Message...")
        messages.append(new_user_message)
    return messages
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
async def interceptUserPrompt(collection, user_message:str, debug:bool=False):
    if collection == 'search':
        collection_name = extract_args(user_message, 1)
        results = await search(user_message, collection_name)
    else:
        results = await search(user_message, collection)
    Log.i("Returning custom SYS Prompt.")
    if debug:
        user_prompt = rag.inject_into_system_prompt(user_message, docs=results)
        print("--User Prompt--")
        print(user_prompt)
        return user_prompt
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

def get_previous_user_messages(json_data):
    # Get the list of messages
    messages = json_data.get('messages', [])
    # Filter to find the last message with role 'user'
    last_user_messages = []
    count = 0
    for message in reversed(messages):
        # if message.get('role') == 'user':
        if count == 0:
            count += 1
            continue
        last_user_messages.append(message.get('content'))
    return last_user_messages
""" HELPER """
def extract_args(input_string, word_count):
    """Extract the first 'word_count' words from the input string."""
    # Split the string into words
    words = input_string.split()
    # Return the first 'word_count' words
    args = words[:word_count]
    Log.i(f"Args: {args}")
    return str(LIST.get(0, args, "")).strip()
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



if __name__ == '__main__':
    port = 11434
    debug = False
    host = "0.0.0.0"
    print(f"Starting Bruno Server. Host={host}, Port={port}, Debug={debug}")
    app.run(host=host, port=port, debug=debug, loop=looper)