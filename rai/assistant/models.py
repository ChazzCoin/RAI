import json
from typing import List, Optional
from pydantic import BaseModel
"""
    -> These are Structured Response Models
"""

class AiResponse:
    def __init__(self, model: str, created_at: Optional[str], done: Optional[bool], done_reason: Optional[str],
                 total_duration: int, load_duration: int, prompt_eval_count: int,
                 prompt_eval_duration: Optional[int], eval_count: Optional[int], eval_duration: Optional[int],
                 embeddings: List[List[float]], response: str):
        self.model = model
        self.created_at = created_at
        self.done = done
        self.done_reason = done_reason
        self.total_duration = total_duration
        self.load_duration = load_duration
        self.prompt_eval_count = prompt_eval_count
        self.prompt_eval_duration = prompt_eval_duration
        self.eval_count = eval_count
        self.eval_duration = eval_duration
        self.embeddings = embeddings
        self.response = response

    def get_response(self):
        if self.response: return self.response
        if self.embeddings: return self.embeddings

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(
            model=data.get('model', None),
            created_at=data.get('created_at', None),
            done=data.get('done', None),
            done_reason=data.get('done_reason', None),
            total_duration=data.get('total_duration', None),
            load_duration=data.get('load_duration', None),
            prompt_eval_count=data.get('prompt_eval_count', None),
            prompt_eval_duration=data.get('prompt_eval_duration', None),
            eval_count=data.get('eval_count', None),
            eval_duration=data.get('eval_duration', None),
            embeddings=data.get('embeddings', None),
            response=data.get('response', None)
        )

class RaiQueryExpander(BaseModel):
    query: Optional[str]

class RaiMetadata(BaseModel):
    title: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    version: Optional[str]
    file_type: Optional[str]
    date_created: Optional[str]
    date_modified: Optional[str]
    tags: List[str]
    author: Optional[str]
    description: Optional[str]
    source: Optional[str]



class TrueFalse(BaseModel):
    result: Optional[bool]

class QuestionAnswer(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

class ListOfQuestionAnswers(BaseModel):
    results: List[QuestionAnswer]

class TrueOrFalse(BaseModel):
    answer: bool

class BaseEvent(BaseModel):
    # Fields from the "table" style event
    attendance: Optional[str] = None
    date_time: Optional[str] = None
    location: Optional[str] = None
    opponent: Optional[str] = None
    score: Optional[str] = None

    # Fields from the "calendar" style event
    attendance_count: Optional[str] = None
    day_number: Optional[str] = None
    description: Optional[str] = None
    end_time: Optional[str] = None
    event_name: Optional[str] = None
    start_time: Optional[str] = None
    weekday: Optional[str] = None