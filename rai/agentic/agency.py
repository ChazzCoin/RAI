import base64
from typing import Optional, Any, List

from pydantic import BaseModel, field_validator, Field


class ApiResponse(BaseModel):
    """
    A universal API response model for standardized communication.

    Attributes:
        success (bool): Indicates whether the API operation was successful.
        data (Optional[Any]): Contains the result or payload data. This can be any JSON serializable object.
        message (Optional[str]): A human-readable message providing context about the response.
        errors (Optional[List[str]]): A list of error messages, if any occurred.
    """
    success: bool = Field(..., description="Indicates if the request was processed successfully.")
    data: Optional[Any] = Field(None, description="Payload data of the response.")
    message: Optional[str] = Field(None, description="Contextual message regarding the response.")
    errors: Optional[List[str]] = Field(None, description="List of error messages, if any.")


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