import asyncio

import rai.internal
import rai.assistant
import rai.ingest
import rai.agentic
from rai.agentic.agent_assistants.knowledge_assist import KnowledgeTool
from rai.agentic.agent_modules.engine import ToolEngine
from rai.assistant.connectors import LLM

# loop = asyncio.get_event_loop()

async def main(request:str):
    knowledge_assistant = ToolEngine.get_tool_engine('knowledge-base')
    result = await knowledge_assistant().self_navigation(request=request)
    print(result)
    return result

# loop.run_until_complete(main("set the prefix to 'referral2025.1'. then give me all the documents i have in that collection."))