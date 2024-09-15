from openai import OpenAI
import os
from dotenv import load_dotenv
from openai.types.chat import ChatCompletion
from F.LOG import Log
load_dotenv()

default_model = os.getenv("DEFAULT_OPENAI_MODEL")
embedding_model = os.getenv("DEFAULT_OPENAI_EMBEDDING_MODEL")

def getClient():
  return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_embeddings(text):
  print('Embedding Model:', embedding_model)
  response = getClient().embeddings.create(
    input=text,
    model=embedding_model
  )
  return response.data[0].embedding

def chat_request(system:str, user:str, model:str=default_model, content_only:bool=True):
  print(f"Model: {model}")
  response = getClient().chat.completions.create(
    model=model,
    response_format={"type": "text"},
    messages=[
      {"role": "system", "content": system },
      {"role": "user", "content": user }
    ]
  )
  print(response)
  if content_only:
    return response.choices[0].message.content
  return response

def chat_request_forward(messages: [], model:str=default_model) -> ChatCompletion:
  response = getClient().chat.completions.create(
    model=model,
    response_format={"type": "text"},
    messages=messages
  )
  return response


if __name__ == "__main__":
  system = "You are a knowledgeable assistant for the Park City Soccer Club, providing information about soccer programs and club activities."
  user = "What are the upcoming events?"
  print(chat_request(system, user))
