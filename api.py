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
# from rai.internal.redisdb import RaiCache
from rai.RAG.Q import query_chroma_by_prefix
from rai import env
from nlp.Categorizer import Topics

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)
app = cors(app, allow_origin="*")

collection_name = "documents"
contexter = ContextHelper()
# cache = RaiCache()
# rag = RAGWithChroma(collection_name=collection_name)
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

RAI_VERSION = "0.5.0:hypercorn"
RAI_FOOTER_MESSAGE = lambda model, text: ""
# RAI_FOOTER_MESSAGE = lambda model, text: f"""\n
# {text}\n
# | Rai Youth Sports Chat | AI Model: {model} | API Version: {RAI_VERSION} |
# """


def decode_and_save_image(encoded_image):
    image_data = base64.b64decode(encoded_image)
    # Write the binary data to a file
    with open('/Users/chazzromeo/Desktop/chat_image.png', 'wb') as f:
        f.write(image_data)
    print('Image successfully saved as output_image.png')

CACHE_KEY_TWO = lambda one, two: f"{one}:{two}"
CACHE_KEY_THREE = lambda one, two, three: f"{one}:{two}:{three}"

PROMPT_CACHE = {

}

def combine(*obj:str):
    result = ""
    for o in obj:
        result = f"{result}\n{o}"
    return result


from rai.data.extraction.intake.PDF_v1 import FPDF
import base64
import imghdr
import io


def decode_base64_to_file(base64_string, output_file_name=None):
    """
    Decodes a base64 string and saves it as a JPEG, PNG, or PDF file.

    :param base64_string: The base64-encoded string.
    :param output_file_name: Optional; name of the output file without extension.
    :return: The path of the saved file.
    """
    # Decode the base64 string
    file_data = base64.b64decode(base64_string)

    # Determine file type
    if file_data.startswith(b'%PDF'):
        file_extension = 'pdf'
        # If it's a PDF, extract the text
        return FPDF.extract_text_from_pdf_bytes(file_data)
    else:
        # Check if it's an image (jpeg or png)
        file_extension = imghdr.what(None, file_data)
        if file_extension not in ['jpeg', 'png']:
            raise ValueError("Unsupported file type: the base64 string does not represent a JPEG, PNG, or PDF file.")

    # Set output file name if not provided
    # output_file_name = output_file_name or 'decoded_file'
    # output_file_path = f"{output_file_name}.{file_extension}"

    # Save the file
    # with open(output_file_path, 'wb') as f:
    #     f.write(file_data)

    return file_data


@app.route('/api/chat/{idx}', methods=['POST', 'OPTIONS'])
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
async def chat_completion(idx:Optional[int]=None):
    print(idx)
    immediate_response_override = False
    immediate_response_message = "Something Seems to have gone wrong."
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
    current_rai_model: str = DICT.get('model', jbody, 'gpt-4o-mini')
    modelIn_data: dict = DICT.get(current_rai_model, RAI_MODs)

    mod_title: str = DICT.get('title', modelIn_data)
    mod_ai_name: str = DICT.get('ai_name', modelIn_data)
    mod_initials: str = DICT.get('initials', modelIn_data, "none")
    mod_flow: str = DICT.get('ai_flow', modelIn_data, "none")
    mod_org_rep_type: str = DICT.get('org_rep_type', modelIn_data)
    mod_collection_prefix: str = DICT.get('collection', modelIn_data, 'none')
    mod_zip_code = DICT.get('zip', modelIn_data, '00000')
    mod_specialty: str = DICT.get('org_specialty', modelIn_data)
    mod_system_prompt_lambda = DICT.get('prompt', modelIn_data) #(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
    mod_context_prompt_lambda = DICT.get('context_prompt', modelIn_data)
    mod_openai_model: str = DICT.get('openai', modelIn_data, 'gpt-4o-mini')
    mod_ollama_model: str = DICT.get('ollama', modelIn_data, 'llama3:latest')

    """ TODO CACHE OUT  """
    # cache_queue = cache.get_queued_chat_data(modelIn)
    weather_cache = None # await get_refresh_cached_weather(current_rai_model, mod_zip_code)

    """     EXTRACT USER MESSAGES AND IMAGES    """
    user_message: str = get_last_user_message(jbody)
    pre_user_messages: list = get_previous_user_messages(jbody)
    user_images: list = get_last_user_images(jbody)

    we_have_file_data = False
    try:
        # TODO: file_data needs to be a list of file_data for each image uploaded...
        file_data = decode_base64_to_file(LIST.get(0, user_images, "Needs Clinical Review!"))
        if file_data: we_have_file_data = True
    except Exception as e:
        print(e)
        file_data = "Needs Clinical Review!"

    """     REAL-TIME DATA INTERCEPTOR    """
    real_time_data = None
    # if weather_cache: # TODO: dynamic....
    #     real_time_data = combine(weather_cache)

    """ System Prompt Overrider """
    if str(user_message).lower().startswith('new prompt'):
        current_message = str(user_message).replace('new prompt', '')
        immediate_response_message = "The New Prompt has been added successfully. Ready to proceed."
        if we_have_file_data:
            # The File is the new prompt (because the message is empty)
            if is_empty_message(current_message):
                fsp = file_data
                immediate_response_override = True
            else:
                # The message is the prompt, the file is the referral.
                fsp = current_message
                user_message = file_data
        else:
            # No file. Message is the prompt.
            fsp = current_message
            immediate_response_override = True
        PROMPT_CACHE[current_rai_model] = fsp
    if str(user_message).lower().startswith('reset prompt'):
        PROMPT_CACHE[current_rai_model] = mod_system_prompt_lambda
        immediate_response_message = "The Prompt has been reset successfully. Ready to proceed."
        immediate_response_override = True

    final_system_prompt = DICT.get(current_rai_model, PROMPT_CACHE, mod_system_prompt_lambda)
    if type(final_system_prompt) not in [str]:
        final_system_prompt = final_system_prompt(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)

    """     USER PROMPT INTERCEPTOR    """
    new_user_message: dict = {
        'role': 'user',
        'content': f"{user_message}"
    }
    messages: list = setupSingleMessageForChatSequence(final_system_prompt, new_user_message)

    if mod_flow == "MRA":
        user_message = f"REFERRAL:\n {file_data}"
        new_user_message: dict = {
            'role': 'user',
            'content': f"{user_message}"
        }

        """     SETUP MESSAGES FOR CHAT SEQUENCE   """
        messages: list = setupSingleMessageForChatSequence(final_system_prompt, new_user_message)
        print(messages)
    elif mod_flow == "MRC":
        new_user_message: dict = {
            'role': 'user',
            'content': f"{user_message}"
        }

        """     SETUP MESSAGES FOR CHAT SEQUENCE   """
        messages: list = setupSingleMessageForChatSequence(final_system_prompt, new_user_message)
        print(messages)
    elif mod_flow == "QA":
        print("Running Query Assistant (QA) Flow.")
        if type(mod_system_prompt_lambda) in [str]:
            ollama_prompt: str = mod_system_prompt_lambda
        else:
            ollama_prompt: str = mod_system_prompt_lambda(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
        ollama_request: str = await ollama_quick_generation(ollama_prompt, user_message, modelIn=mod_ollama_model, debug=True)

        """ CONTEXT ANALYZER """
        # query_context_name = analyze_context(ollama_request, default="general")

        user_message: str = queryModelCollection(
            mod_collection_prefix, "open",
            user_message=user_message,
            context_message=ollama_request,
            debug=False
        )
        new_user_message: dict = {
            'role': 'user',
            'content': f"{user_message}"
        }
        messages: list = setupMessagesForChatSequence(final_system_prompt, messages, new_user_message)

    print("\n\n -- Query+UserMessage -- \n\n")
    print(user_message)
    print("\n\n")
    appended_response: str = ""
    """ Response Override """
    if immediate_response_override:
        appended_response = immediate_response_message
    else:
        """     GENERATE AI CHAT RESPONSE   """
        if isOpenAI(current_rai_model):
            ai_response: str = await openai_chat_generation(messages, modelIn=mod_openai_model, debug=True)
        else:
            ai_response: str = await ollama_chat_generation(messages, modelIn=mod_ollama_model, debug=True)
        """ TODO    CACHE IN    """
        # cache.queue_chat_data(modelIn, ai_response)
        """     FOOTER MESSAGE     """
        appended_message = RAI_FOOTER_MESSAGE(mod_openai_model, "")
        """     PREPARE AND SEND FINAL RESPONSE     """
        appended_response = appender(response_message=ai_response, message_to_append=appended_message)
    """ Response Override """
    final_response: dict = to_chat_response(appended_response, role="assistant", options=jbody['options'])
    print("\n\n -- Final Response -- \n\n")
    print(final_response)
    print("\n\n")
    return Response(f"\n{json.dumps(final_response)}\n", content_type='text/event-stream')

def isOpenAI(model:str) -> bool:
    if model.startswith("llama"):
        return False
    return True
def is_empty_message(input_str: str) -> bool:
    # Check if input is None or an empty string after stripping whitespace
    if input_str is None or input_str.strip() == "":
        return True
    return False
"""
CONTEXT ANALYZER
"""
def analyze_context(request_in: str, default:str):
    r = default

    def analyzer(user_input:str):
        results = Topics.RUN_MAIN_CATEGORIZER(user_input)
        return results

    try:
        user_context = analyzer(request_in)
        if user_context:
            r = LIST.get(0, user_context, default)
        print(r)
    except Exception as e:
        print(e)

    return r


""" 
CACHE WEATHER
"""
async def get_refresh_cached_weather(model, zip):
    weather_cache = "" #cache.get_weather_data(model)
    # if weather_cache:
    #     return weather_cache
    # weather_result = get_weather_by_zip(zip)
    # air_quality = await get_air_quality(zip)
    # weather_report = f"{weather_result}\n{air_quality}"
    # cache.cache_weather_data(model, f"Current Weather and Air Quality Data for {zip}\n{weather_report}\n")
    return "weather_report"

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
def setupSingleMessageForChatSequence(system_prompt, new_user_message):
    return [
            {'role': 'system', 'content': system_prompt},
            new_user_message
        ]
def setupMessagesForChatSequence(system_prompt, messages, new_user_message):
    if type(new_user_message) in [list, tuple] and len(messages) <= 1:
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
def search(user_message:str, *base_paths:str):
    # embeds = await get_embeddings(user_message)
    results = query_chroma_by_prefix(*base_paths, query=user_message, k=25)
    Log.i("Search Result Count:", results)
    return results
"""     
USER PROMPT INTERCEPTOR   
"""
def queryModelCollection(*base_paths, user_message:str, context_message:str, debug:bool=False):
    documents = ""
    try:
        # if collection == 'search':
        #     collection_name = extract_args(user_message, 1)
        #     results = search(f"{user_message} {context_message}", collection_name)
        # else:
        #
        results = query_chroma_by_prefix(*base_paths, query=user_message, k=10)
        if results:
            docs:[] = DICT.get("documents", results, [])
            documents = '\n'.join(LIST.flatten(docs))
            return documents
        Log.i("Returning custom SYS Prompt.")
        if debug:
            user_prompt = "rag.inject_into_system_prompt(user_message, specialty=specialty, docs=results, text=pre_text)"
            print("--User Prompt--")
            print(user_prompt)
            return user_prompt
        return results
    except Exception as e:
        Log.e("Failed to query", e)
        return documents
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