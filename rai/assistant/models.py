import json
from typing import List, Optional
from pydantic import BaseModel

from rai.base.BaseFormats import register_format

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

