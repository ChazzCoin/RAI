import requests, json


def ollama_request_chat(prompt:str, content:str, model:str="llama3", forward:bool=False):
    url = "http://192.168.1.6:11434/api/chat"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "model": model,
        "messages": [
            { "role": "system", "content": prompt },
            { "role": "user", "content": content }
        ],
        "stream": False
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
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


def get_ollama_models(api_url="http://192.168.1.6:11434/api/models"):
    """
    Call the Ollama API to retrieve models data.
    :param api_url: The URL for the Ollama models endpoint.
    :return: A list of models or an error message.
    """
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQzMDM5N2NlLWVkN2EtNDIxMi05NTUzLWE1ZTAyNjUwMjVkMSJ9.w82jx_2M_-ikF5sXM6TKlopenWfQF9pw0aqDqw1AGos"
    try:
        # Make a GET request to the Ollama /api/models endpoint
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + key,
                   "User-Agent": "Ollama-Client/1.0"
                   }
        response = requests.get(api_url, headers=headers)

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
