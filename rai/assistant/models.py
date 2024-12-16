
from rai.assistant.openai_client import generate_structured_output
from typing import List, Optional
from pydantic import BaseModel
"""
    -> These are Structured Response Models
"""

class TrueFalse(BaseModel):
    result: Optional[bool]

class QuestionAnswer(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

class ListOfQuestionAnswers(BaseModel):
    results: List[QuestionAnswer]

