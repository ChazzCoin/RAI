import base64
from typing import Optional, Any

from pydantic import BaseModel, field_validator


class Agency(BaseModel):
    session_id: str
    prefix: str
    user_prompt: str
    system_prompt: Optional[str]
    tool: Optional[str]
    task: Optional[str]
    flow: Optional[str]
    agent: Optional[str]
    data: Optional[str]

    @field_validator("data")
    def encode_data_to_base64(cls, v):
        if isinstance(v, bytes):
            return base64.b64encode(v).decode('utf-8')
        return v