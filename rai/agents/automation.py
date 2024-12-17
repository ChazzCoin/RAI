import re
from abc import abstractproperty, abstractmethod

import requests
from rai.assistant.connectors import RaiAi
from langchain import PromptTemplate
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Tuple, Optional
from enum import Enum

from langchain_huggingface import HuggingFaceEmbeddings

from rai.assistant.models import ListOfQuestionAnswers, RaiMetadata, QuestionAnswer
from rai.assistant.openai_client import generate_structured_output
from rai.data.loaders.rai_loaders.JsonDataLoader import JSONDataLoader

hugging_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
ollama_embeddings = OllamaEmbeddings(model="llama3")

from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

from langchain_chroma import Chroma
# vector_store = Chroma(embedding_function=embeddings)

ai = RaiAi().OLLAMA

"""
1. A True/False model and Structured Response
2. A Question/Answer Generation Response
3.  
"""
DOCUMENT_MAX_TOKENS = 4000
DOCUMENT_OVERLAP_TOKENS = 100
FRAGMENT_MAX_TOKENS = 128
FRAGMENT_OVERLAP_TOKENS = 16
QUESTIONS_PER_DOCUMENT = 40

def ask_openai_for_true_or_false(api_key, question):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4-0613",  # Use the model version that supports function calling
        "messages": [
            {"role": "user", "content": question}
        ],
        "functions": [
            {
                "name": "answer_question",
                "description": "Provide a boolean answer to the given question.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The question being answered."},
                        "answer": {"type": "boolean", "description": "The boolean answer to the question."}
                    },
                    "required": ["question", "answer"]
                }
            }
        ],
        "function_call": {"name": "answer_question"}  # Explicitly invoke the function
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        # Extract the structured response from the function call
        function_response = result["choices"][0]["message"]["function_call"]["arguments"]

        # Parse the structured JSON
        import json
        structured_data = json.loads(function_response)

        # Ensure the format and return the boolean answer
        if (
            isinstance(structured_data, dict) and
            "answer" in structured_data and
            isinstance(structured_data["answer"], bool)
        ):
            return structured_data["answer"]
        else:
            raise ValueError(f"Invalid response format: {structured_data}")

    except Exception as e:
        print(f"Error: {e}")
        return None



class DataGenerator:

    results = None
    json_obj_list:[] = None

    @abstractmethod
    def run(self, dataset): pass
    @abstractmethod
    def system_prompt(self): pass
    @abstractmethod
    def to_json(self): pass

    def to_dataloader(self):
        if self.json_obj_list:
            loader = JSONDataLoader(json_objects=self.json_obj_list)
            if loader:
                return loader
            else:
                return None
        else:
            self.to_json()
            if self.json_obj_list:
                loader = JSONDataLoader(json_objects=self.json_obj_list)
                if loader:
                    return loader
                else:
                    return None

    @staticmethod
    def format_dataset(dataset):
        temp = "DATASET:\n"
        if type(dataset) in [list, tuple]:
            for item in dataset:
                temp = f"{temp}\n{item}"
        elif type(dataset) in [str]:
            temp = dataset
        elif type(dataset) in [dict]:
            for key, value in dataset.items():
                temp = f"{temp}\n{key}: {value}"
        return temp


class MetadataDG(DataGenerator):

    def run(self, dataset):
        try:
            results = generate_structured_output(
                user_prompt=self.format_dataset(dataset),
                system_prompt=self.system_prompt(),
                format=RaiMetadata
            )
            results: RaiMetadata
            return results.model_dump_json(exclude_defaults=True)
        except Exception as e:
            print(f"Error: {e}")
            return None

    def system_prompt(self):
        return f"""
        You will read the following content and you will extract out the following metadata details for vector database and query optimizations.
        1. Look at each key name in the model and then try to determine the value for the key, based on the content.
        2. Try to guess the overall context and attempt to fill out all attributes even if you don't know.
        """

    def to_json(self):
        pass

class QuestionAndAnswerDG(DataGenerator):

    def run(self, dataset):
        self.results = generate_structured_output(
            user_prompt=self.format_dataset(dataset),
            system_prompt=self.system_prompt(),
            format=ListOfQuestionAnswers
        )
        print(self.results)
        return self.results

    def to_json(self):
        try:
            if self.results and type(self.results) in [list, tuple]:
                for item in self.results:
                    temp = {
                        "question": item.question,
                        "answer": item.answer
                    }
                    self.json_obj_list.append(temp)
        except Exception as e:
            print(f"Error: {e}")
            return None




    def system_prompt(self):
        return """
        You will take the following dataset and you will generate accurate questions and corresponding answers.
        1. Questions: should be the most likely asked human questions based on the context of the information.
        2. Answers: should be detailed and as accurate as possible.
        Rule: If you do not know that answer, do not make something up. Just do not include that question and answer.
        """




if __name__ == "__main__":
    from rai.data.extraction.parsers.PDF_v1 import FPDF
    # import asyncio
    data = FPDF.extract_text_from_pdf("/Users/chazzromeo/Desktop/pcsc2024/general/Park City Soccer Club LTADM.pdf").strip()
    data = data[:int(len(data)*0.5)]
    # QuestionAndAnswerGenerator().run(data)
    # asyncio.run(QuestionAndAnswerGenerator().run(data))