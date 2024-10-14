#!/bin/bash
import asyncio
import base64
import json
import os.path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import aiohttp
from quart import Quart, request, jsonify, Response, send_file
from quart_cors import cors
import requests
from F import DICT, LIST
from F.LOG import Log
from F.DATE import get_timestamp_str as get_current_timestamp
from rai.RaiModels import RAI_MODs, getRaiModels
from chdb.rag import RAGWithChroma
from rai.agents.weather import get_weather_by_zip, get_air_quality
from rai.assistant.context import ContextHelper
from rai.internal.redisdb import RaiCache
from rai.RAG.newmain import query_chroma_by_user_auth
from rai import env


Log = Log("RAI API Bruno Canary")
app = Quart(__name__)
app = cors(app, allow_origin="*")

collection_name = "documents"
contexter = ContextHelper()
cache = RaiCache()
rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

RAI_VERSION = "0.5.0:hypercorn"
RAI_FOOTER_MESSAGE = lambda model, text: f"""\n
{text}\n
| Rai Youth Sports Chat | AI Model: {model} | API Version: {RAI_VERSION} |
"""


def decode_and_save_image(encoded_image):
    image_data = base64.b64decode(encoded_image)
    # Write the binary data to a file
    with open('/Users/chazzromeo/Desktop/chat_image.png', 'wb') as f:
        f.write(image_data)
    print('Image successfully saved as output_image.png')

CACHE_KEY_TWO = lambda one, two: f"{one}:{two}"
CACHE_KEY_THREE = lambda one, two, three: f"{one}:{two}:{three}"

def combine(*obj:str):
    result = ""
    for o in obj:
        result = f"{result}\n{o}"
    return result

@app.route('/api/chat/{idx}', methods=['POST', 'OPTIONS'])
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
async def chat_completion(idx:Optional[int]=None):
    print(idx)
    """     GRAB HEADERS   """
    request.headers['Content-Type'] = 'application/json'
    # print(f"Headers received: {headers}")

    """     PARSE REQUEST IN    """
    data = await request.get_data(cache=True, parse_form_data=True)
    if not data:
        data = await request.get_json(force=True, silent=False, cache=True)
    jbody: dict = json.loads(data.decode('utf-8'))

    """     GET CHAT DETAILS      """
    # chat_id requires new Rai Chat UI...
    chat_id = DICT.get('chatId', jbody, 'default')
    messages: list = jbody.get('messages', [])


    """     GET MAPPED MODEL      """
    request_in_model: str = DICT.get('model', jbody, 'gpt-4o-mini')
    modelIn_data: dict = DICT.get(request_in_model, RAI_MODs)

    mod_title: str = DICT.get('title', modelIn_data)
    mod_ai_name: str = DICT.get('ai_name', modelIn_data)
    mod_org_rep_type: str = DICT.get('org_rep_type', modelIn_data)
    mod_collection: str = DICT.get('collection', modelIn_data, 'none')
    mod_zip_code = DICT.get('zip', modelIn_data, '00000')
    mod_specialty: str = DICT.get('org_specialty', modelIn_data)
    mod_system_prompt_lambda = DICT.get('prompt', modelIn_data)(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
    mod_context_prompt_lambda = DICT.get('context_prompt', modelIn_data)
    mod_openai_model: str = DICT.get('openai', modelIn_data, 'gpt-4o-mini')
    mod_ollama_model: str = DICT.get('ollama', modelIn_data, 'llama3:latest')

    """ TODO     CACHE OUT    """
    # cache_queue = cache.get_queued_chat_data(modelIn)
    weather_cache = None # await get_refresh_cached_weather(request_in_model, mod_zip_code)

    """     EXTRACT USER MESSAGES AND IMAGES    """
    user_message: str = get_last_user_message(jbody)
    pre_user_messages: list = get_previous_user_messages(jbody)
    user_images: list = get_last_user_images(jbody)

    """     REAL-TIME DATA INTERCEPTOR    """
    real_time_data = None
    if weather_cache: # TODO: dynamic....
        real_time_data = combine(weather_cache)

    """     USER PROMPT INTERCEPTOR    """
    if mod_collection != "none":
        ollama_prompt: str = mod_context_prompt_lambda(pre_user_messages)
        ollama_request: str = await ollama_quick_generation(ollama_prompt, user_message, modelIn=mod_ollama_model, debug=True)
        user_message: str = interceptUserPrompt(
            collection=mod_collection,
            user_message=user_message,
            context_message=ollama_request,
            specialty=mod_specialty,
            pre_text=real_time_data,
            debug=True
        )

    new_user_message: dict = {
        'role': 'user',
        'content': f"{user_message}"
    }

    """     SETUP MESSAGES FOR CHAT SEQUENCE   """
    messages: list = setupMessagesForChatSequence(mod_system_prompt_lambda, messages, new_user_message)

    """     GENERATE AI CHAT RESPONSE   """
    if isOpenAI(request_in_model):
        ai_response: str = await openai_chat_generation(messages, modelIn=mod_openai_model, debug=True)
    else:
        ai_response: str = await ollama_chat_generation(messages, modelIn=mod_ollama_model, debug=True)

    """ TODO    CACHE IN    """
    # cache.queue_chat_data(modelIn, ai_response)

    """     FOOTER MESSAGE     """
    appended_message: str = RAI_FOOTER_MESSAGE(mod_openai_model, "")

    """     PREPARE AND SEND FINAL RESPONSE     """
    appended_response: str = appender(response_message=ai_response, message_to_append=appended_message)
    final_response: dict = to_chat_response(appended_response, role="assistant", options=jbody['options'])
    return Response(f"\n{json.dumps(final_response)}\n", content_type='text/event-stream')

def isOpenAI(model:str) -> bool:
    if model.startswith("llama"):
        return False
    return True

""" 
CACHE WEATHER
"""
async def get_refresh_cached_weather(model, zip):
    weather_cache = cache.get_weather_data(model)
    if weather_cache:
        return weather_cache
    weather_result = get_weather_by_zip(zip)
    air_quality = await get_air_quality(zip)
    weather_report = f"{weather_result}\n{air_quality}"
    cache.cache_weather_data(model, f"Current Weather and Air Quality Data for {zip}\n{weather_report}\n")
    return weather_report

""" 
GENERATE AI CHAT RESPONSE 
"""
async def openai_chat_generation(messages:[], modelIn:str="gpt-4o-mini", debug:bool=False):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env.OPENAI_API_KEY}',
    }
    data = {
        'model': modelIn,
        'messages': messages,
        'temperature': 0,
        'stream': False,
        'store': True,
        'metadata': {
            'chat_id': '',
            'model_org': "park-city:latest",
            'collection': "parkcitysc-new",
            'version': RAI_VERSION
        }
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
async def ollama_chat_generation(messages:[], modelIn:str="llama3:latest", debug:bool=False):
    """Asynchronously get chat completion from OpenAI API."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {env.OPENAI_API_KEY}',
    }
    data = {
        'model': modelIn,
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
        'Authorization': f'Bearer {env.OPENAI_API_KEY}',
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
def search(user_message:str, collection_name:str):
    # embeds = await get_embeddings(user_message)
    results = query_chroma_by_user_auth(user_auth="ADMIN", collection_prefix=collection_name, query=user_message)
    Log.i("Search Result Count:", results)
    return results
"""     
USER PROMPT INTERCEPTOR   
"""
def interceptUserPrompt(collection, user_message:str, context_message:str, specialty:str, pre_text:str=None, debug:bool=False):
    if collection == 'search':
        collection_name = extract_args(user_message, 1)
        results = search(f"{user_message} {context_message}", collection_name)
    else:
        results = search(f"{user_message} {context_message}", collection)
    Log.i("Returning custom SYS Prompt.")
    if debug:
        user_prompt = rag.inject_into_system_prompt(user_message, specialty=specialty, docs=results, text=pre_text)
        print("--User Prompt--")
        print(user_prompt)
        return user_prompt
    return rag.inject_into_system_prompt(user_message, specialty=specialty, docs=results, text=pre_text)
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

def get_last_user_images(json_data):
    # Get the list of messages
    messages = json_data.get('messages', [])
    # Filter to find the last message with role 'user'
    last_user_message = None
    for message in reversed(messages):
        if message.get('role') == 'user':
            last_user_message = message.get('images', [])
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
def to_chat_response(message:str, role:str="user", model:str="gpt-4o-mini", isDone:bool=False, options:dict={}):
    return {
        "model": model,
        "created_at": get_current_timestamp(),
        "message": {
            "chat_id": 'chazzromeo',
            "role": role,
            "content": message
        },
        "options": options,
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
    print("version", request.args)
    return jsonify({
        "version": "0.1.45",
    }), 200
@app.route('/api/tags', methods=['GET'])
def models_api():
    print("Calling Models", request.headers)
    return getRaiModels()
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