import rai.internal
import rai.assistant
import rai.ingest
import rai.agentic
from rai.assistant.connectors import LLM
from rai.ingest.utilities.text_data import schedule_text


print(LLM.tool("summarize", user_prompt=schedule_text))