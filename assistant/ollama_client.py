import requests, json, logging
from requests.exceptions import HTTPError, RequestException
from assistant.models import ApiEngines as engines
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_ollama_model(name, insecure=False, stream=True, timeout=60):
    if not name:
        print("Model name must be provided.")
        raise ValueError("Model name must be provided.")

    headers = {'Content-Type': 'application/json'}
    payload = {'name': name}

    if insecure:
        payload['insecure'] = True
    if not stream:
        payload['stream'] = False

    try:
        with requests.post(engines.OLLAMA.route("/api/pull"), headers=headers, data=json.dumps(payload), stream=stream, timeout=timeout) as response:
            response.raise_for_status()  # Raise HTTPError for bad responses

            if stream:
                status = None
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            print(f"Received data: {data}")
                            status = data.get('status')
                            # Handle progress updates or other actions here
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            continue
                return status
            else:
                data = response.json()
                print(f"Received data: {data}")
                return data.get('status')
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        raise
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
        raise
def ollama_request_chat(prompt:str, content:str, model:str=None, forward:bool=False):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "model": engines.OLLAMA.default_model(override=model),
        "messages": [
            { "role": "system", "content": prompt },
            { "role": "user", "content": content }
        ],
        "stream": False
    }
    response = requests.post(engines.OLLAMA.route("/api/chat"), headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        if forward:
            return response
        response_data = response.json()
        print(response_data)
        return response_data['message']['content']
    else:
        if response:
            return response
        return {"error": f"Request failed with status code {response.status_code}"}
def get_ollama_models():
    """
    Call the Ollama API to retrieve models data.
    :param api_url: The URL for the Ollama models endpoint.
    :return: A list of models or an error message.
    """
    key = ""
    try:
        # Make a GET request to the Ollama /api/models endpoint
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + key,
                   "User-Agent": "Ollama-Client/1.0"}
        response = requests.get(engines.OLLAMA.route("/api/models"), headers=headers)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            # Parse the JSON response and return the models data
            print(response.json())
            models_data = response.json()
            return models_data
        else:
            # Return an error message if the status code is not 200
            print(f"Request failed with status code {response.status_code}")
            return {"error": f"Failed to retrieve models, status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        # Catch any errors during the HTTP request
        return {"error": str(e)}
def list_ollama_running_models(timeout=60):
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.get(engines.OLLAMA.route("/api/ps"), headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()
        logger.info(f"Received data: {data}")

        models = data.get('models', [])
        print(models)
        return models

    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        raise
    except RequestException as req_err:
        logger.error(f"Request error occurred: {req_err}")
        raise
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error: {json_err}")
        raise
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise
def generate_ollama_embedding(text, timeout=60):

    if not text:
        logger.error("Prompt must be provided.")
        raise ValueError("Prompt must be provided.")

    headers = {'Content-Type': 'application/json'}
    payload = {
        'model': engines.OLLAMA.embeddings_model(),
        'input': text
    }

    try:
        response = requests.post(engines.OLLAMA.route("/api/embed"), headers=headers, data=json.dumps(payload), timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()
        logger.info(f"Received data: {data}")

        if 'embeddings' in data:
            return data.get('embeddings', [])
        else:
            logger.error("Embedding not found in the response.")
            raise ValueError("Embedding not found in the response.")

    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        raise
    except RequestException as req_err:
        logger.error(f"Request error occurred: {req_err}")
        raise
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error: {json_err}")
        raise
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise


if __name__ == "__main__":
    # download_ollama_model('mxbai-embed-large')
    # list_ollama_running_models()
    input_text = ["Why is the sky blue?", "Why is the grass green?"]
    try:
        embeddings = generate_ollama_embedding(
            input_text=input_text
        )
        print(f"Embeddings: {embeddings}")
    except Exception as e:
        print(f"An error occurred: {e}")