from collections import deque
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from rai.agentic.agent_tools.result import ToolResult
from rai.agentic.ai_plugins.reason import Objectives
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel

class ToolPlan(BaseModel):
    mode: str = "next-step"
    initial_request: str = ""
    user_data: Optional[Dict[str, str]] = None
    role: str = "**You control a web browser interactively.**"
    user_request: str = ""
    objectives: Objectives = Objectives()
    overall_objective: str = "Unknown Objective"
    overall_plan: str = "Unknown Plan"

    summary_report: str = "Nothing has happen"

    actions: List[dict[str, Any]] = []
    decisions_made: List[str] = []

    search_term_queue: deque[str] = deque([])

    step_queue: deque[NextStepModel] = deque([])
    overflow_step_queue: List[NextStepModel] = []
    steps_taken: List[NextStepModel] = []
    previous_step: Optional[NextStepModel] = None
    current_step: Optional[NextStepModel] = None

    required_data: Optional[Dict[str, str]] = None
    max_steps: int = 10
    current_step_count: int = 0

    current_state: ToolResult = ToolResult()
