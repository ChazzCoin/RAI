import re
import types
from abc import abstractmethod, ABC
from typing import List, Dict, Type, overload

import requests
from F import DICT
from pydantic import BaseModel


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


"""
1. User Prompt/Data In

2. Specific Task

3. Decision (Again/Finish)

4. Result


"""



    # print(AgentFormatTrueOrFalse().run(
    #     "I want to create something...",
    #     """
    #     **Is the user asking a question or making a request for me to give them something?**
    #     *Do they want me to give them back something based on the context of their words?*
    #     """
    # ))

    # from rai.data.extraction.parsers.PDF_v1 import FPDF
    # # import asyncio
    # data = FPDF.extract_text_from_pdf("/Users/chazzromeo/Desktop/pcsc2024/general/Park City Soccer Club LTADM.pdf").strip()
    # data = data[:int(len(data)*0.5)]
    # QuestionAndAnswerGenerator().run(data)
    # asyncio.run(QuestionAndAnswerGenerator().run(data))