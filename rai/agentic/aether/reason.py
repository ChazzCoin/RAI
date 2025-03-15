from abc import ABC, abstractmethod
from typing import Optional
from pydantic import Field
from rai.agentic.aether.base import BaseAgent
from rai.agentic.aether.aellm import AeLLM
from rai.agentic.aether.schema import AgentState, Memory


"""
Abstract Class to Blueprint the flow.
"""

class AEtherAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    ai: Optional[AeLLM] = Field(default_factory=AeLLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @staticmethod
    def module_name() -> str: return "AEther Agent"

    """ AEther Core Reasoning """

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()

    """ AEther Core Setup """
