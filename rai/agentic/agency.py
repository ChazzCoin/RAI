import base64
from typing import Optional, Any, List, Type

from pydantic import BaseModel, field_validator, Field
from rai.agentic import agent_assistants
from rai.agentic.agent_modules.engine import TOOL_ENGINE_REGISTRY, ToolEngine


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

    @classmethod
    def get_tool_engine(cls, name: str) -> Type[ToolEngine]:
        return TOOL_ENGINE_REGISTRY.get(name)[0]

    @classmethod
    def get_tool_list(cls) -> List[str]:
        tools = []
        for k,v in TOOL_ENGINE_REGISTRY.items():
            tools.append(k)
        return tools

if __name__ == '__main__':
    print(Agency.get_tool_list())