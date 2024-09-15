# import requests
#
#
# def get_openai_models():
#     """
#     Call the OpenAI /v1/models endpoint to retrieve the list of available models.
#     """
#     url = "http://192.168.1.6:11434/api/tags"
#     headers = { "Content-Type": "application/json" }
#     try:
#         # Make a GET request to the /v1/models endpoint
#         response = requests.get(url, headers=headers)
#         # Check if the response is successful
#         if response.status_code == 200:
#             return response.json()  # Return the list of models
#         else:
#             return {"error": f"Failed to retrieve models, status code: {response.status_code}"}
#     except requests.exceptions.RequestException as e:
#         return {"error": str(e)}
#
#
# # Example usage
# if __name__ == "__main__":
#     api_key = "your_openai_api_key_here"  # Replace with your actual OpenAI API key
#     models_data = get_openai_models(api_key)
#     print(models_data)
