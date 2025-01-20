import asyncio
from abc import abstractmethod, ABC

from F import DICT
from rai.data.utilities.text_data import schedule_text
from typing_extensions import overload
from queue import Queue
from threading import Thread
from rai.assistant.connectors import RaiAi
from rai.base.BaseFormats import RaiBaseFormats
from rai.base.BaseFunctions import RaiBaseFunctions
from rai.base.BasePrompts import RaiBasePrompts
from rai.data.utilities.TextUtils import TextProcessor
from rai.models import functions
import concurrent
from concurrent.futures import ThreadPoolExecutor
AGENT_REGISTRY = {}
CONTEXTS = {
    "is_event": {
        "prompt": """
            You are an AI assistant that strictly returns the Boolean truth value of a given statement—no additional text or commentary.
            **Only respond with the single word "True" or "False".**
        """,
        "context": "Generate a list of question/answer pairs based on the above data in the specified format."
    },
    "faq": {
        "prompt": """
            You are an AI assistant designed to analyze data and generate insightful questions and corresponding answers based on the provided content. Your responses must strictly adhere to the following structured format:

            [
                {"question": "<Generated Question 1>", "answer": "<Generated Answer 1>"},
                {"question": "<Generated Question 2>", "answer": "<Generated Answer 2>"},
                ...
            ]

            Instructions:
            1. Provide **at least one Q/A pair**, but generate as many as the data supports.
            2. Each **answer** should be **lengthy and detailed**, giving thorough explanations, context, examples, or historical background (if appropriate).
            3. Do not include any commentary, explanations, or text outside the specified JSON structure.
            4. Do not provide keys other than `"question"` and `"answer"`.
        """,
        "context": "QUESTION:\nIs the user asking about a calendar based event like a sports game, practice, meeting, festival, etc..."
    },
    "categorize_sports_primary": {
        "prompt": """
            You are an intelligent AI that identifies relevant function calls from the provided function definitions ("functions") based on the user's prompt.
            Instructions:
            - Treat each function name in the "functions" list as a Topic/Category.
            - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
            - Return the function calls (in a specific format) that match the user's needs.
        """,
        "context": """
            Youth Soccer Club
        """,
    },
    "categorize_sports_secondary": {
        "prompt": """
        You are an intelligent AI that identifies relevant function calls from the provided function definitions ("functions") based on the user's prompt.
        Instructions:
        - Treat each function name in the "functions" list as a Topic/Category.
        - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
        - Return the function calls (in a specific format) that match the user's needs.
    """,
        "context": """
        Youth Soccer Club
    """,
    },
    "metadata": {
        "prompt": """
            You are an AI assistant tasked with extracting metadata from a given piece of text. You must produce a single JSON object that strictly follows the structure below:

            Instructions:
            1. Return only the JSON object above—no additional text or keys.
            2. Fill the fields with accurate, relevant information derived from the user-provided text.
            3. If a particular field is not found or cannot be reasonably inferred, leave it as an empty string or an empty array (for "tags").
            4. Do not include any commentary, explanation, or keys outside this structure.
        """,
        "context": """
            Based on the format provided, fill out the values as best as you can.
        """
    },
    "": {
        "prompt": """
        You are an AI assistant
    """,
        "context": "",
    },
    "context_expander": {
        "prompt": """
        You are an AI assistant
    """,
        "context": """

    """,
    },
}


def register_agent(name: str):
    def decorator(cls):
        AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


class RaiBaseAgent(ABC, RaiAi, TextProcessor):
    name = None

    @classmethod
    def get_registry(cls): return AGENT_REGISTRY

    @classmethod
    def pipeline(cls, name: str, user_prompt: str, system_prompt: str=None, sub=False):
        agent_classes = AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt, sub=sub)

    @classmethod
    async def pipeline_async(cls, name: str, user_prompt: str, system_prompt: str=None, sub=False):
        agent_classes = AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(user_prompt=user_prompt, system_prompt=system_prompt, sub=sub)

    @abstractmethod
    def type(self): pass
    @abstractmethod
    def parse(self, result): pass
    def prompt(self): return RaiBasePrompts.pipeline(self.name)
    def agent_context(self): return DICT.get(self.name, CONTEXTS, {})
    def system_prompt(self):
        temp = self.prompt()
        if temp: return temp
        return DICT.get("prompt", self.agent_context())
    def context(self): return DICT.get("context", self.agent_context(), "")
    def prompter(self, user_prompt): return f"USER PROMPT:\n{user_prompt}\n{self.context()}"

    def run(self, user_prompt, system_prompt=None, sub=False):
        try:
            if self.type() == "format":
                return self.parse(self.engine.generate_format(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt() if not system_prompt else system_prompt,
                    format=RaiBaseFormats.pipeline(self.name)
                ))
            elif self.type() == "function":
                return self.parse(self.engine.generate_function(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt() if not system_prompt else system_prompt,
                    functions=RaiBaseFunctions.pipeline(self.name, sub=sub)
                ))
            elif self.type() == "base":
                return self.parse(self.engine.generate(
                    user=user_prompt,
                    system=self.system_prompt() if not system_prompt else system_prompt
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

    async def run_async(self, user_prompt, system_prompt=None, sub=False):
        try:
            if self.type() == "format":
                return self.parse(await self.engine.generate_format_async(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt() if not system_prompt else system_prompt,
                    format=RaiBaseFormats.pipeline(self.name)
                ))
            elif self.type() == "function":
                return self.parse(await self.engine.generate_function_async(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt() if not system_prompt else system_prompt,
                    functions=RaiBaseFunctions.pipeline(self.name, sub=sub)
                ))
            elif self.type() == "base":
                return self.parse(await self.engine.generate_async(
                    user=user_prompt,
                    system=self.system_prompt() if not system_prompt else system_prompt
                ))
        except Exception as e:
            print(f"Error: {e}")
            return None

"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
- remove term of service issues
- summarize data
- 
"""
@register_agent("generate")
class AgentConfigGenerate(RaiBaseAgent):
    def type(self): return "base"
    def parse(self, result): return result

@register_agent("rag")
class AgentConfigRAG(RaiBaseAgent):
    def type(self): return "base"
    def parse(self, result): return result

@register_agent("summarize")
class AgentConfigSummarize(RaiBaseAgent):
    def type(self): return "base"
    def parse(self, result): return result

@register_agent("objective")
class AgentConfigObjective(RaiBaseAgent):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_agent("categorize_sports")
class AgentConfigCategorizeSports(RaiBaseAgent):
    def type(self): return "function"
    def parse(self, result): return self.parse_function_names(result)

@register_agent("context_expander")
class AgentConfigPromptExpander(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.query

@register_agent("metadata")
class AgentConfigMetadata(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result

@register_agent("urls")
class AgentConfigUrls(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("contextual_groups")
class AgentConfigContextualGroups(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("faq")
class AgentConfigQuestionAnswer(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("is_event")
class AgentConfigIsEvent(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.answer

@register_agent("is_true")
class AgentConfigIsTrue(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.answer

@register_agent("events")
class AgentConfigEvents(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("contacts")
class AgentConfigContacts(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("locations")
class AgentConfigLocations(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder

@register_agent("step_by_step")
class AgentConfigStepByStep(RaiBaseAgent):
    def type(self): return "format"
    def parse(self, result): return result.holder


async def main():
    from rai.data.utilities.text_data import schedule_text
    results = await RaiBaseAgent.pipeline_async(
            name="summarize",
            user_prompt=schedule_text
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)

if __name__ == "__main__":
    # from rai.data.utilities.text_data import schedule_text
    asyncio.run(
        main()
    )