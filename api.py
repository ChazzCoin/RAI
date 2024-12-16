#!/bin/bash
import asyncio
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
from rai.assistant.context import ContextHelper
from rai.internal.connectors import REDIS_DB_CLIENT, PostgresTables, VECTOR_DB_CLIENT
from rai import env
from nlp.Categorizer import Topics
from rai.data.extraction.parsers.PDF_v1 import FPDF
import base64
import imghdr

from rai.models.models import AIModelData

Log = Log("RAI API Bruno Canary")
app = Quart(__name__)
app = cors(app, allow_origin="*")

contexter = ContextHelper()
looper = asyncio.get_event_loop()
executor = ThreadPoolExecutor(max_workers=1)

""" DATABASES """
collection_name = "documents"
RAI_CACHE = REDIS_DB_CLIENT
RAI_MODELS = PostgresTables.AI_Models()
CHAT_ARCHIVE = PostgresTables.ChatArchive()

STORED_RAI_MODELS: [AIModelData] = RAI_MODELS.get_all_ai_models()
print("Stored RAI Models", STORED_RAI_MODELS)

IMAGE_FOLDER = f"{os.path.dirname(__file__)}/files/images"

RAI_VERSION = "0.5.0:hypercorn"
RAI_FOOTER_MESSAGE = lambda model, text: ""

CACHE_KEY_TWO = lambda one, two: f"{one}:{two}"
CACHE_KEY_THREE = lambda one, two, three: f"{one}:{two}:{three}"

image_path = '/Users/chazzromeo/Desktop/chat_image.jpg'


def decode_and_save_image(encoded_image):
    image_data = base64.b64decode(encoded_image)
    # Write the binary data to a file
    with open('/Users/chazzromeo/Desktop/chat_image.jpg', 'wb') as f:
        f.write(image_data)
    print('Image successfully saved as output_image.jpg')
def decode_base64_to_file(base64_string):
    file_data = base64.b64decode(base64_string)
    if file_data.startswith(b'%PDF'):
        return FPDF.extract_text_from_pdf_bytes(file_data)
    else:
        file_extension = imghdr.what(None, file_data)
        if file_extension not in ['jpeg', 'png']:
            raise ValueError("Unsupported file type: the base64 string does not represent a JPEG, PNG, or PDF file.")
    return file_data

class UserRequest:
    chat_id: str = "guest"
    user_id: str = "guest"
    user_name: str = "guest"
    user_email: str = "guest"
    user_role: str = "guest"
    def __init__(self, body:dict=None):
        if not body: return
        self.chat_id = DICT.get('chatId', body, 'default')
        self.user_id = DICT.get('user_id', body, 'default')
        self.user_name = DICT.get('username', body, 'default')
        self.user_email = DICT.get('user_email', body, 'default')
        self.user_role = DICT.get('user_role', body, 'default')
        self.cache_in()
    def cache_in(self): return RAI_CACHE.set_key(self.user_name, self.buildUser())
    def cache_out(self): return RAI_CACHE.get_key(self.user_name, default=self.buildUser())
    def buildUser(self):
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "user_role": self.user_role
        }


@app.route('/api/chat/{idx}', methods=['POST', 'OPTIONS'])
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
async def chat_completion(idx:Optional[int]=None):
    """     GRAB HEADERS   """
    request.headers['Content-Type'] = 'application/json'

    """     PARSE REQUEST IN    """
    data = await request.get_data(cache=True, parse_form_data=True)
    if not data:
        data = await request.get_json(force=True, silent=False, cache=True)
    jbody: dict = json.loads(data.decode('utf-8'))

    """     GET CHAT SEQUENCE DETAILS      """
    MessageContext = ChatSequence(jbody)
    MessageContext.ai_response = "Something Seems to have gone wrong."

    """     GET MAPPED MODEL      """
    current_rai_model: str = DICT.get('model', jbody, 'gpt-4o-mini')
    stored_model: AIModelData = RAI_MODELS.get_ai_model_by_name(current_rai_model)
    print(stored_model)

    modelIn_data: dict = DICT.get(current_rai_model, RAI_MODs)
    mod_title: str = DICT.get('title', modelIn_data)
    mod_ai_name: str = DICT.get('ai_name', modelIn_data)
    # mod_initials: str = DICT.get('initials', modelIn_data, "none")
    mod_flow: str = DICT.get('ai_flow', modelIn_data, "none")
    mod_org_rep_type: str = DICT.get('org_rep_type', modelIn_data)
    mod_collection_prefix: str = DICT.get('collection', modelIn_data, 'none')
    # mod_zip_code = DICT.get('zip', modelIn_data, '00000')
    mod_specialty: str = DICT.get('org_specialty', modelIn_data)
    mod_system_prompt_lambda = DICT.get('prompt', modelIn_data) #(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
    # mod_context_prompt_lambda = DICT.get('context_prompt', modelIn_data)
    mod_openai_model: str = DICT.get('openai', modelIn_data, 'gpt-4o-mini')
    mod_ollama_model: str = DICT.get('ollama', modelIn_data, 'llama3:latest')

    """ System Prompt Overrider """
    PROMPT_CACHE = RAI_CACHE.get_key(current_rai_model)
    if str(MessageContext.get_last_user_message).lower().startswith('new prompt'):
        current_message = str(MessageContext.get_last_user_message).replace('new prompt', '')
        MessageContext.ai_response = "The New Prompt has been added successfully. Ready to proceed."
        if MessageContext.has_file:
            # The File is the new prompt (because the message is empty)
            if is_empty_message(current_message):
                fsp = MessageContext.file_data
                MessageContext.immediate_response_override = True
            else:
                # The message is the prompt, the file is the referral.
                fsp = current_message
                MessageContext.modify_last_user_message(MessageContext.file_data)
        else:
            # No file. Message is the prompt.
            fsp = current_message
            MessageContext.immediate_response_override = True
        PROMPT_CACHE[current_rai_model] = fsp
    if str(MessageContext.get_last_user_message).lower().startswith('reset prompt'):
        PROMPT_CACHE[current_rai_model] = mod_system_prompt_lambda
        MessageContext.ai_response = "The Prompt has been reset successfully. Ready to proceed."
        MessageContext.immediate_response_override = True

    # Set the System Prompt
    final_system_prompt = DICT.get(current_rai_model, PROMPT_CACHE, mod_system_prompt_lambda)
    if type(final_system_prompt) not in [str]:
        final_system_prompt = final_system_prompt(mod_ai_name, mod_title, mod_org_rep_type, mod_specialty)
    # Finish Up
    MessageContext.set_system_prompt(final_system_prompt)
    RAI_CACHE.set_key(current_rai_model, PROMPT_CACHE)
    """
    1. Message pass through
        - Append AI Response
        
    2. Modify and Append
        - Modify Last User Message
        - Append AI Response
        
    3. Ignore and Force Single
        - Ignore all old messages.
        - Essentially reset. 3 final messages, [system, user, assistant]
        
    TODO: 
    1. FIX message setup. Not adding the custom system prompt properly.
    2. Handle query flow better. Returning metadata.
    3. Finalize File Intake and metadata setup.
    4. Update the website front-end.
    5. Setup docker compose yaml file.
    6. Make Sure all setup is in a script or built in.
    7. Adding chat archiving back.
    
    """
    if mod_flow == "MRA":
        MessageContext.make_single(user_content=f"REFERRAL:\n {MessageContext.file_data}", system_prompt=final_system_prompt)
    elif mod_flow == "MRC":
        MessageContext.make_single(system_prompt=final_system_prompt)
    elif mod_flow == "QA":
        user_message = VECTOR_DB_CLIENT.queryModelCollection(
            mod_collection_prefix, "open",
            user_message=MessageContext.get_last_user_message,
            k=20
        )
        if user_message:
            MessageContext.modify_last_user_message(user_message)
        else:
            MessageContext.ai_response = "Sorry! No Results found, please try and provide more details and I will try again!"
            MessageContext.immediate_response_override = True

    """ GENERATE AI CHAT RESPONSE """
    if not MessageContext.bypass_ai:
        if isOpenAI(current_rai_model):
            MessageContext.ai_response = await openai_chat_generation(MessageContext.get_messages(), modelIn=mod_openai_model, debug=True)
        else:
            MessageContext.ai_response = await ollama_chat_generation(MessageContext.get_messages(), modelIn=mod_ollama_model, debug=True)

    """ Response Override """
    response = MessageContext.stream_response()
    return Response(f"\n{json.dumps(response)}\n", content_type='text/event-stream')


async def stream_json_payload(json_payload):
    # Use payload to send the response or make an HTTP call
    return Response(f"\n{json.dumps(json_payload)}\n")

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

class ChatSequence:
    body: {} = {}
    options: {} = {}
    system_prompt = "You are a helpful assistant"
    last_user_message = ""
    messages = []
    is_single = False
    is_first = False
    has_file = False
    file_data = None
    files = []
    needs_system_prompt = False
    _user: UserRequest = UserRequest()
    ai_response = ""
    immediate_response_override = False

    def __init__(self, body: {}, system_prompt=None):
        self.body = body
        self.messages = body.get('messages', [])
        self.options = DICT.get('options', body, {})
        self.system_prompt = system_prompt if system_prompt else "You are a helpful assistant"
        self.last_user_message = self.get_last_user_message
        self._user = UserRequest(body)
        self.parse_images()
        print("Messages Length", len(self.messages))
        if self.messages and len(self.messages) >= 1:
            self.is_single = True
        first_message = LIST.get(0, self.messages, {})
        first_role = DICT.get("role", first_message, "")
        if first_role and str(first_role) != "system":
            self.needs_system_prompt = True

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        if self.needs_system_prompt:
            new_messages = [self.build_single_message('system', system_prompt)]
            new_messages.extend(self.messages)
            self.messages = new_messages

    def modify_last_user_message(self, new_content:str):
        last_message = LIST.get(-1, self.messages, {})
        last_content = DICT.get("content", last_message, "")
        modified_content = f"{new_content}\nUser's Request: {last_content}"
        new_messages = self.messages[:-1]
        new_messages.append(self.build_single_message('user', modified_content))
        self.messages = new_messages

    def make_single(self, user_content:str=None, system_prompt:str=None):
        self.messages = self.singleMessageResponse(user_content if user_content else self.last_user_message, system_prompt if system_prompt else self.system_prompt)

    def get_messages(self, is_single_message:bool = False, user_content:str=None, system_prompt:str=None):
        if is_single_message: self.make_single(f"{self.get_last_user_message}\n{user_content}", system_prompt)
        return self.messages

    def parse_images(self):
        try:
            self.file_data = decode_base64_to_file(LIST.get(0, self.last_user_images, "Needs Clinical Review!"))
            if self.file_data: self.has_file = True
            for img in self.last_user_images:
                temp = decode_base64_to_file(img)
                self.files.append(temp)
        except Exception as e:
            print(e)
            self.file_data = "Needs Clinical Review!"

    @property
    def bypass_ai(self): return self.immediate_response_override

    @staticmethod
    def build_single_message(role='system', content=""):
        return {'role': role, 'content': content}

    def singleMessageResponse(self, user_content:str, system_prompt=None):
        if system_prompt: self.system_prompt = system_prompt
        return [
            self.build_single_message('system', self.system_prompt),
            self.build_single_message('user', user_content)
        ]

    def yield_messages(self, startWithLatestMessage=True):
        if not self.messages: return
        if startWithLatestMessage:
            for message in reversed(self.messages):
                yield message
        else:
            for message in self.messages:
                yield message

    @property
    def get_last_user_message(self) -> Optional[str]:
        last_user_message = None
        for message in self.yield_messages():
            if message.get('role') == 'user':
                last_user_message = message.get('content')
                break
        return last_user_message
    @property
    def last_user_images(self) -> list:
        last_user_message = None
        for message in self.yield_messages():
            if message.get('role') == 'user':
                last_user_message = message.get('images', [])
                break
        return last_user_message
    @property
    def previous_user_messages(self) -> list:
        last_user_messages = []
        count = 0
        for message in self.yield_messages():
            if count == 0:
                count += 1
                continue
            last_user_messages.append(message.get('content'))
        return last_user_messages

    """ Back To User """
    def stream_response(self, ai_response:str=None):
        return {
            "model": 'gpt-4o-mini',
            "created_at": get_current_timestamp(),
            "message": {
                "chat_id": self._user.chat_id,
                "role": "assistant",
                "content": ai_response if ai_response else self.ai_response,

            },
            "options": self.options,
            "done": False
        }

def setupSingleMessageForChatSequence(system_prompt, new_user_message):
    return [
            { 'role': 'system', 'content': system_prompt },
            new_user_message
        ]
def setupMessagesForChatSequence(system_prompt, messages, new_user_message):
    if type(new_user_message) in [list, tuple] and len(messages) <= 1:
        Log.i("Creating New Message...")
        temp = [
            { 'role': 'system', 'content': system_prompt },
            LIST.get(0, messages, new_user_message)
        ]
        messages = temp
    else:
        Log.i("Appending New Message...")
        messages.append(new_user_message)
    return messages

"""     
USER PROMPT INTERCEPTOR   
"""


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
def extract_args(input_string, word_count):
    """Extract the first 'word_count' words from the input string."""
    # Split the string into words
    words = input_string.split()
    # Return the first 'word_count' words
    args = words[:word_count]
    Log.i(f"Args: {args}")
    return str(LIST.get(0, args, "")).strip()
""" HELPER """
"""
"files": [{ "type": "image", "url": f"data:image/png;base64,{file_to_base64()}" }]
"""
def to_chat_response(message:str, role:str="user", model:str="gpt-4o-mini", isDone:bool=False, options:dict={}):
    return {
        "model": model,
        "created_at": get_current_timestamp(),
        "message": {
            "chat_id": 'chazzromeo',
            "role": role,
            "content": message,

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