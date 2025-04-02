import datetime
from collections import deque
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from rai.agentic.agent_modules.result import ToolResult
from rai.agentic.pending.reason import Objectives, Checkpoints
from rai.agentic.ai_tools.text_tools.text_formats import NextStepModel, RequiredActions

PLAN_TYPES = {
    "deep_research": "User Prompt Context Involves ongoing, exploratory research that continuously gathers, documents, and summarizes evolving insights on a given topic.",
    "targeted_search": "User Prompt Context Involves finding one or more specific pieces of information, concluding once the exact answer or data is located.",
    "compare_contrast": "User Prompt Context Involves analyzing two or more topics by summarizing findings and highlighting their similarities and differences for a comparative report.",
    "summarization_reporting": "User Prompt Context Involves aggregating information from diverse sources and condensing it into a clear, digestible summary report.",
    "synthesis_integration": "User Prompt Context Involves combining disparate pieces of information to form new insights or a unified narrative.",
    "trend_pattern_analysis": "User Prompt Context Involves analyzing historical and current data to identify patterns or emerging trends over time.",
    "predictive_analysis": "User Prompt Context Involves using existing data and trends to forecast future outcomes or scenarios for proactive decision-making.",
    "diagnostic_analysis": "User Prompt Context Involves investigating issues or anomalies to identify the root causes and provide actionable insights.",
    "decision_support_recommendations": "User Prompt Context Involves synthesizing data to offer strategic advice and actionable recommendations for decision-making.",
    "feasibility_risk_assessment": "User Prompt Context Involves evaluating the viability of a project or idea by assessing potential risks, benefits, and cost-benefit factors.",
    "content_generation_ideation": "User Prompt Context Involves generating creative ideas or content by leveraging research and synthesizing gathered information.",
    "monitoring_alerting": "User Prompt Context Involves continuously tracking data or systems for changes, providing real-time updates and alerts when specific conditions are met.",
    "workflow_automation_optimization": "User Prompt Context Involves streamlining processes by automating repetitive tasks and optimizing resource allocation for efficiency.",
    "strategic_roadmapping_planning": "User Prompt Context Involves developing a long-term strategic plan with clear milestones, timelines, and resource allocation.",
    "data_aggregation_visualization": "User Prompt Context Involves collecting data from multiple sources and presenting it in visual formats like dashboards or infographics for clarity.",
    "fact_checking_verification": "User Prompt Context Involves validating the accuracy and credibility of information from various sources to ensure reliable outcomes.",
    "scenario_analysis_simulation": "User Prompt Context Involves exploring multiple 'what-if' scenarios through simulation and comparative analysis to assess potential outcomes.",
    "user_interaction_personalization": "User Prompt Context Involves tailoring outputs based on individual user preferences, context, or feedback loops to enhance engagement."
}

class ToolPlan(BaseModel):
    mode: str = "next-step"
    initial_request: str = ""
    prefix: str = "general2025.1"
    session_id: str = "general2025.1"
    user_data: Optional[Dict[str, str]] = { "username": "myname@gmail.com", "password": "somepassword1" }
    role: str = "**You control a web browser interactively.**"
    plan_type: str = "checkpoints"
    plan_type_description: str = ""
    user_request: str = ""
    objectives: Objectives = Objectives()
    overall_objective: str = "Unknown Objective"
    end_goal: str = "Unknown End Goal"
    overall_plan: str = "Unknown Plan"
    checkpoints: List[Checkpoints] = []

    summary_report: str = "Nothing has happen"
    current_state_summary: str = "Nothing has happen"
    decisions_and_actions_summary: str = "Nothing has happen"
    action_timeline_summary: str = "Nothing has happen"
    action_timeline: Dict[int, str] = { int(datetime.datetime.utcnow().timestamp()): 'Lets Begin..'}

    actions: List[dict[str, Any]] = []
    decisions_made: List[str] = []
    current_decision: str = ""

    search_term_queue: deque[str] = deque([])

    max_checkpoints: int = 50
    step_mode: str = "checkpoint" # vs 'step'


    current_checkpoint_count: int = 0
    checkpoint_queue: deque[NextStepModel] = deque([])
    overflow_checkpoint_queue: List[NextStepModel] = []
    checkpoints_made: List[NextStepModel] = []
    previous_checkpoint: Optional[str] = None
    pending_checkpoint: Optional[str] = None
    current_checkpoint: Optional[str] = None

    current_check_step_count: int = 0
    check_step_queue: deque[NextStepModel] = deque([])
    overflow_check_step_queue: List[NextStepModel] = []
    check_steps_made: List[NextStepModel] = []
    previous_check_step: Optional[str] = None
    pending_check_step: Optional[str] = None
    current_check_step: Optional[str] = None

    required_data: str = "None"
    required_actions: RequiredActions = []
    current_state: ToolResult = ToolResult()

    def get_plan_type_description(self) -> str:
        try:
            return PLAN_TYPES[self.plan_type]
        except KeyError:
            return "None"

