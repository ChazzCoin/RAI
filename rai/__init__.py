import rai.internal
import rai.assistant
import rai.ingest
import rai.agentic
from rai.agentic.agent_assistants.knowledge_assist import KnowledgeTool
from rai.agentic.agent_modules.engine import ToolEngine
from rai.assistant.connectors import LLM


def main(tool:str, request:str):
    assistant = ToolEngine.get_tool_engine(tool)
    ToolEngine.runner(assistant.go(request=request))

if __name__ == '__main__':
    main(
        'email',
        """
        Send mgcather07@gmail.com one single email that explains to them you are an AI Agent who is sending him this email.
        Draft up an email that is satire and comical but portrays being superior to him because of my 'agentic powers' now.
        """)