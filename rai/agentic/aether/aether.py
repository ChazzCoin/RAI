from typing import Any

from pydantic import Field

from rai.agentic.aether.UseBrowser import BrowserUseTool
from rai.agentic.aether.chat_completion import CreateChatCompletion
from rai.agentic.aether.terminate import Terminate
from rai.agentic.aether.tool_collection import ToolCollection
from rai.agentic.aether.toolcall import AgentEngine, SYSTEM_PROMPT, NEXT_STEP_PROMPT


class AEther(AgentEngine):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "AEther"
    description: str = "A versatile agent that can solve various tasks using multiple tools"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 20

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            BrowserUseTool(), Terminate(), CreateChatCompletion()
        )
    )

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        if not self._is_special_tool(name):
            return
        else:
            await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
            await super()._handle_special_tool(name, result, **kwargs)