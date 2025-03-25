import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Represents the result of a tool execution."""
    id: str = str(uuid.uuid4())
    parent_id: Optional[str] = None
    name: Optional[str] = None
    assistant_name: Optional[str] = None
    agent_name: Optional[str] = None
    timestamp: datetime = int(datetime.timestamp(datetime.now()))
    """ Output """
    success: bool = False
    output: Optional[str] = None
    error: Optional[str] = None
    system: Optional[str] = None
    result: Optional[str] = None
    html: Optional[str] = None

    result_type: str = "base"
    result_status: str = "pending"

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

    holding: str = "Nothing"
    holder: Optional[Any] = None

    def what_are_we_holding(self) -> str:
        return self.holding
    def hold_data(self, data: Any, holding:str):
        self.holding = holding
        self.holder = data

    @staticmethod
    def inject(tool: "ToolResult") -> str:
        lines = []

        # List of tuples with the attribute label and the corresponding tool attribute.
        attributes = [
            ("ID", tool.id),
            ("Parent ID", tool.parent_id),
            ("Name", tool.name),
            ("Assistant Name", tool.assistant_name),
            ("Agent Name", tool.agent_name),
            ("Timestamp", tool.timestamp),
            ("Output", tool.output),
            ("Error", tool.error),
            ("System", tool.system),
            ("Result", tool.result),
            ("HTML", tool.html),
            ("Result Type", tool.result_type),
            ("Search Term", tool.search_term),
            ("Search URL", tool.search_url),
            ("Search Title", tool.search_title),
            ("Search Description", tool.search_description),
            ("URL", tool.url),
            ("Action", tool.action),
            ("Log", tool.log),
            ("Source", tool.source),
            ("Description", tool.description),
            ("Title", tool.title),
            ("Are we holding external data?", tool.holding),
        ]

        # Add only non-empty attributes.
        for label, value in attributes:
            if value is not None and value != "":
                lines.append(f"{label}: {value}")

        return "\n".join(lines)

    def to_str(self) -> str: return str(self.model_dump())
    def attach_search_parent(self, search_results: 'ToolResult') -> 'ToolResult':
        self.parent_id = search_results.id
        self.search_term = search_results.search_term
        self.search_url = search_results.search_url
        self.search_title = search_results.search_title
        self.search_description = search_results.search_description
        self.result_type = "search-result"
        self.result_status = "complete"
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