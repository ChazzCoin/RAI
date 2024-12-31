import re
from abc import abstractmethod, ABC
from typing import List, Dict, Type

import requests
from pydantic import BaseModel

from rai.assistant.connectors import RaiAi
# from langchain import PromptTemplate
# from pydantic import BaseModel, Field
# from typing import Any, Dict, List, Tuple, Optional
# from enum import Enum
#
# from langchain_huggingface import HuggingFaceEmbeddings

from rai.assistant.models import ListOfQuestionAnswers, RaiMetadata, QuestionAnswer, RaiQueryExpander, TrueOrFalse
from rai.data.loaders.rai_loaders.JsonDataLoader import JSONDataLoader

# hugging_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# from langchain_ollama import ChatOllama
# from langchain_ollama import OllamaEmbeddings
# ollama_embeddings = OllamaEmbeddings(model="llama3")
#
# from langchain_openai import OpenAI
# from langchain_openai import ChatOpenAI
# from langchain_openai import OpenAIEmbeddings
# openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
#
# from langchain_chroma import Chroma
# # vector_store = Chroma(embedding_function=embeddings)



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


"""
{
  "type": "table",
  "headers": ["Date", "Drill", "Focus"],
  "rows": [
    ["Jan 10", "Cone Dribble Warm-up", "Ball Control"],
    ["Jan 12", "1v1 Challenge", "Defensive Skills"]
  ]
}


{
  "formatted_markdown": ""
}



"""
class ResponseRow(BaseModel):
    row: List[str]

class FormatResponseMarkdown(BaseModel):
    markdown: str

class FormatResponseTable(BaseModel):
    type: str
    headers: List[ResponseRow]
    rows: List[ResponseRow]

class ResponseFormatPipeline(ABC):

    pipelines: Dict[str, Type['ResponseFormatPipeline']] = {}

    ai = RaiAi(engine_name='ollama')
    results = None
    json_obj_list:[] = None

    def __init_subclass__(cls, *, pipeline: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if not pipeline:
            raise ValueError("Subclasses must define an 'engine' name.")
        cls.engine = pipeline
        ResponseFormatPipeline.pipelines[pipeline] = cls

    @classmethod
    def pipeline(cls, name): return cls().pipelines[name]

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



class DataGenerator:
    ai = RaiAi(engine_name='ollama')
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
class PromptExpander(DataGenerator):

    def run(self, query, context="General"):
        try:
            self.results:RaiQueryExpander = self.ai.engine.generate_format(
                user=self.format_dataset(query),
                system=self.system_prompt(context=context),
                format=RaiQueryExpander
            )
            return self.results
        except Exception as e:
            print(f"Error: {e}")
            return None

    def system_prompt(self, context:str="General"):
        return f"""
        **You will read the following User Query and add Proper context tag words to enhance vector RAG queries.**
        **User the following Topic/Category as contextual reference for enhancement.**
        **Only return the new query**
        CONTEXTUAL REFERENCE [ {context} ]
        """

    def to_json(self):
        pass
class MetadataDG(DataGenerator):

    def run(self, dataset):
        try:
            results = self.ai.engine.generate_format(
                user=self.format_dataset(dataset),
                system=self.system_prompt(),
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
        self.results = self.ai.engine.generate_format(
            user=self.format_dataset(dataset),
            system=self.system_prompt(),
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
class TrueOrFalseDG(DataGenerator):

    def run(self, query, question:str="Is this a question or statement?"):
        return self.ai.engine.generate_format(query, self.system_prompt(question=question), format=TrueOrFalse)

    def to_json(self):
       pass

    def system_prompt(self, question:str=""):
        return f"""
        **You will take the following user request/query for RAG Chat and then answer the following question based on the query.**
        **You will only response with a True or False.**
        -> Question: {question}
        Rule: If you do not know that answer, default to False.
        """
class MarkDownFormatPipeline(ResponseFormatPipeline, pipeline="markdown"):
    def run(self, query):
        return self.ai.engine.generate_format(
            user=query,
            system=self.system_prompt(),
            format=FormatResponseMarkdown
        )
    def system_prompt(self):
        return """
        **You are a professional, detailed and robust AI Chat Response Formatter.**
        **You will take the following dataset and you will format it as Markdown to give a cleaner and easier format to read.**
        **Do not alter or modify the data given, only format it.**
        """
    def to_json(self): pass

# ResponseFormatPipeline.pipeline('markdown').run(dataset="")

class Categorizer(DataGenerator):
    def run(self, query:str, categories:str):
        self.results = self.ai.engine.generate_format(
            user=query,
            system=self.system_prompt(categories=categories),
            format=FormatResponseMarkdown
        )
        print(self.results)
        return self.results
    def system_prompt(self, categories="general"):
        return """
        **You are a RAG Query Context To Category Matcher**
        **Based on the following 'Topics' / 'Categories' provided, you will read the User Query and match the context of the Query with one of the given categories.**
        **Rule: Only return the category within the formatted structured output.**
        
        --CATEGORIES TO MATCH:
            Industry: Youth Sports Soccer for Players/Parents/Coaches/Office Admins
        
            1. ''
            Description: 
            
            2. ''
            Description: 
            
            3. ''
            Description: 
            
            4. ''
            Description: 
            
        --DEFAULT CATEGORY IF NO MATCH = 'general'
        """
    def to_json(self): pass
class RaiQuestions:
    question_or_request = "Is the user asking a question or making a request for me to give them something?"


if __name__ == "__main__":

    TrueOrFalseDG().run(
        "Do we have practice this week?",
        """
        **Is the user asking about a calendar or date based event?**
        *A practice, game, tournament, meeting, party, anything that might have a calendar based event.*
        """
    )
    TrueOrFalseDG().run(
        "I want to create something...",
        """
        **Is the user asking a question or making a request for me to give them something?**
        *Do they want me to give them back something based on the context of their words?*
        """
    )

    # from rai.data.extraction.parsers.PDF_v1 import FPDF
    # # import asyncio
    # data = FPDF.extract_text_from_pdf("/Users/chazzromeo/Desktop/pcsc2024/general/Park City Soccer Club LTADM.pdf").strip()
    # data = data[:int(len(data)*0.5)]
    # QuestionAndAnswerGenerator().run(data)
    # asyncio.run(QuestionAndAnswerGenerator().run(data))