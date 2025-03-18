import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

class ToolResults:
    name: Optional[str] = None
    data: List['ToolResult'] = []
    def add_result(self, tool: 'ToolResult'): self.data.append(tool)
    def add_and_pass(self, tool: 'ToolResult') -> 'ToolResult':
        self.data.append(tool)
        return tool
    def count_results(self) -> int: return len(self.data)
    def to_str(self) -> str: return "\n".join([item.to_str() for item in self.data])
    def order_by_timestamp(self, descending: bool = False):
        self.data.sort(key=lambda x: x.timestamp, reverse=descending)
    def get_oldest(self) -> Optional['ToolResult']:
        return min(self.data, key=lambda x: x.timestamp, default=None)
    def get_newest(self) -> Optional['ToolResult']:
        return max(self.data, key=lambda x: x.timestamp, default=None)
    def find_all_equals(self, attribute: str, value: Any) -> List['ToolResult']:
        return [item for item in self.data if getattr(item, attribute, None) == value]

class ToolResult(BaseModel):
    """Represents the result of a tool execution."""
    id: str = str(uuid.uuid4())
    parent_id: Optional[str] = None
    name: Optional[str] = None
    assistant_name: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: Optional[datetime] = int(datetime.timestamp(datetime.now()))
    """ Output """
    output: Optional[str] = None
    error: Optional[str] = None
    system: Optional[str] = None
    result: Optional[str] = None
    html: Optional[str] = None

    result_type: str = "base"

    search_term: Optional[str] = None
    search_url: Optional[str] = None
    search_title: Optional[str] = None
    search_description: Optional[str] = None

    url: Optional[str] = None
    action: Optional[str] = None
    log: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None

    def to_str(self) -> str: return str(self.model_dump())
    def attach_search_parent(self, search_results: 'ToolResult') -> 'ToolResult':
        self.parent_id = search_results.id
        self.search_term = search_results.search_term
        self.search_url = search_results.search_url
        self.search_title = search_results.search_title
        self.search_description = search_results.search_description
        self.result_type = "search-result"
        return self
    def create_search_results(self, tool_results:  List['ToolResult']) -> List['ToolResult']:
        results = []
        for tool_result in tool_results:
            copied = self.model_copy()
            copied.attach_search_parent(tool_result)
            results.append(copied)
        return results
    def attach_parent(self, id: str) -> 'ToolResult':
        self.parent_id = id
        return self
    def attach_result(self, obj: str) -> "ToolResult":
        self.result = obj
        return self
    def get_url(self, is_search:bool=False) -> str:
        if self.search_url and is_search: return self.search_url
        else: return self.url
    def merge(self, other: 'ToolResult') -> 'ToolResult':
        """Merge another ToolResult into this one, prioritizing other's non-null values."""
        for field_name, value in other.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(self, field_name, value)
        return self

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional = None