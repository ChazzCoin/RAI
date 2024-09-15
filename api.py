#!/bin/bash
import json
from os import system

import gevent.pywsgi
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.bridge import routeBridge_blueprint
from assistant import openai_client, api

BLUEPRINTS = [routeBridge_blueprint]

app = Flask(__name__)
for bp in BLUEPRINTS:
    app.register_blueprint(bp)
CORS(app)
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

@app.route("/ollama/api/version", methods=['GET'])
def version_ollama():
    return {
        "version": 'latest',
    }
@app.route("/api/version", methods=['GET'])
def version():
    return jsonify({
        "version": "0.1.45",
    }), 200

@app.route("/version", methods=['GET'])
def versions():
    return jsonify({
        "version": "0.1.45",
    }), 200
@app.route('/api/tags', methods=['GET'])
def models_api():
    """
    Call the OpenAI /v1/models endpoint to retrieve the list of available models.
    """
    print("Calling Models")
    url = "http://192.168.1.6:11434/api/tags"
    headers = {"Content-Type": "application/json"}
    try:
        # Make a GET request to the /v1/models endpoint
        response = requests.get(url, headers=headers)
        # Check if the response is successful
        if response.status_code == 200:
            return response.json()  # Return the list of models
        else:
            return jsonify({"error": f"Failed to retrieve models, status code: {response.status_code}"})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)})

# Configure OpenAI API key
default_model = "gpt-4o"
CHAT_MESSAGE_OPENAI = lambda system, user: [
      {"role": "system", "content": system },
      {"role": "user", "content": user }
    ]



ChatID = ""
@app.route('/chat/completed', methods=['POST'])
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
@app.route('/api/chat', methods=['POST'])
def chat_middleware():
    """
    {
        'messages': [
            {'content': 'hey', 'images': [], 'role': 'user'},
            {'content': '', 'images': [], 'role': 'assistant'},
            {'content': 'hey', 'images': [], 'role': 'user'},
            {'content': '', 'images': [], 'role': 'assistant'},
            {'content': 'hey', 'images': [], 'role': 'user'},
            {'content': '', 'images': [], 'role': 'assistant'},
            {'content': 'hey', 'images': [], 'role': 'user'} ],
            'model': 'llama3:latest', 'options': {'temperature': 0}, 'stream': False
    }
    :return:
    """
    print(request)
    """ FROM USER """
    string_data = request.data.decode('utf-8')
    user_data = json.loads(string_data)
    print(user_data)
    """ INLET """
    # modified_user_data = inlet(user_data)
    """ FORWARDING """
    role = user_data["messages"][-1]["role"]
    messages = user_data["messages"]
    message = messages[-1]["content"]
    # openai_response = openai_client.chat_request(system=role, user=message)
    # openai_response = openai_client.chat_request_forward(messages=messages)
    response = api.ollama_request_chat("you are a useful assistant", message, forward=True)
    """ OUTLET """
    # modified_openai_response = outlet(openai_response)
    """ TO USER """
    obj_response = bytes_to_string(response.content)
    json_response = json.loads(obj_response)
    print(obj_response)
    return obj_response

def bytes_to_string(byte_data: bytes, encoding: str = 'utf-8') -> str:
    if not isinstance(byte_data, bytes):
        raise ValueError("Input must be a byte string.")
    try:
        # Decode the byte string using the specified encoding
        return byte_data.decode(encoding)
    except Exception as e:
        raise ValueError(f"Decoding failed: {e}")
"""
{ 'model': 'gpt4o-mini', 'message': [] }

webui
{
    "model": "llama3:latest",
    "messages": [
        {
            "id": "6b5b6db9-7ed1-4268-a9d4-d115581c3348",
            "role": "user",
            "content": "hey",
            "timestamp": 1725989004
        },
        {
            "id": "973695d2-8fd8-4453-b1ae-dd6b957dd3b0",
            "role": "assistant",
            "content": "Hey! How's it going?",
            "info": {
                "total_duration": 4521280995,
                "load_duration": 4196604290,
                "prompt_eval_count": 11,
                "prompt_eval_duration": 47952000,
                "eval_count": 8,
                "eval_duration": 234033000
            },
            "timestamp": 1725989004
        }
    ],
    "chat_id": "c4a22ad4-b076-4214-85e0-c105ba942667"
}
"""
@app.route('/api/chats', methods=['POST'])
def chats():
    """
    Mimic the /chat process where the user sends a message (prompt),
    and the server responds with a generated answer.
    """
    # Get the JSON data sent by the user (e.g., the prompt)
    data = request.get_json()
    print(data)
    # Ensure the request contains a 'message' field
    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    # Mimic processing the input prompt
    user_message = data['message']

    # Example: Mimic a response generation process
    if "hello" in user_message.lower():
        bot_response = "Hello! How can I assist you today?"
    elif "bye" in user_message.lower():
        bot_response = "Goodbye! Have a great day!"
    else:
        bot_response = "I'm just a simple bot, but I can mimic a response!"

    # Return the response as a JSON object
    response = {
        "user_message": user_message,
        "bot_response": bot_response
    }

    return jsonify(response), 200

@app.route('/chat', methods=['POST'])
def chat():
    """
    Mimic the /chat process where the user sends a message (prompt),
    and the server responds with a generated answer.
    """
    # Get the JSON data sent by the user (e.g., the prompt)
    data = request.get_json()

    # Ensure the request contains a 'message' field
    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    # Mimic processing the input prompt
    user_message = data['message']

    # Example: Mimic a response generation process
    if "hello" in user_message.lower():
        bot_response = "Hello! How can I assist you today?"
    elif "bye" in user_message.lower():
        bot_response = "Goodbye! Have a great day!"
    else:
        bot_response = "I'm just a simple bot, but I can mimic a response!"

    # Return the response as a JSON object
    response = {
        "user_message": user_message,
        "bot_response": bot_response
    }

    return jsonify(response), 200

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
    app.run(host=host, port=port, debug=debug)
    # app_server = gevent.pywsgi.WSGIServer((host, port), app)
    # app_server.serve_forever()


