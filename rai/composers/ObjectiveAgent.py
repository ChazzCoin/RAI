import asyncio
import threading
from abc import abstractmethod, ABC

from F import DICT, LIST

from rai.base.BaseAgents import RaiBaseAgent
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
OBJECTIVE_PROMPT_REGISTRY = {}

def register_objective_prompt(name: str):
    """
    Decorator that calls the decorated function one time immediately
    (when the code is imported) and stores the returned value in BASE_PROMPTS.
    """
    def decorator(func):
        # Call the function immediately at decoration time.
        initial_value = func()
        # Store that return value in the dictionary
        OBJECTIVE_PROMPT_REGISTRY[name] = initial_value

        def wrapper():
            return initial_value
        return wrapper
    return decorator


class RaiObjectiveAgent(ABC, RaiAi, TextProcessor):
    name = None

    # @classmethod
    # def get_registry(cls): return OBJECTIVE_GENT_REGISTRY

    # @classmethod
    # def pipeline(cls, name: str, user_prompt: str, system_prompt: str=None, sub=False):
    #     agent_classes = OBJECTIVE_GENT_REGISTRY.get(name)
    #     if not agent_classes: return None
    #     cls.name = name
    #     agent_cls = agent_classes[0]
    #     agent_instance = agent_cls()
    #     return agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt, sub=sub)

    @classmethod
    async def pipeline_async(cls, user_prompt: str, data: str):
        agent_instance = cls()
        return await agent_instance.run_async(user_prompt=user_prompt, data=data)

    # @abstractmethod
    # def type(self): pass
    # @abstractmethod
    # def parse(self, result): pass
    def prompt(self, name): return OBJECTIVE_PROMPT_REGISTRY.get(name)
    def agent_context(self): return ""
    def system_prompt(self):
        temp = self.prompt()
        if temp: return temp
        return DICT.get("prompt", self.agent_context())
    def context(self): return DICT.get("context", self.agent_context(), "")
    def prompter(self, user_prompt, data): return f"KNOWLEDGE LIBRARY:\n{data}\nUSER PROMPT:\n{user_prompt}"

    async def run_async(self, user_prompt, data):
        try:
            results = RaiBaseAgent.pipelines(
                "objective", "subject",
                user_prompt=user_prompt
            )
            objectives = DICT.get("objective", results, [])
            objective = LIST.get(0, objectives, "general")
            subject = DICT.get("subject", objectives, "")
            system_prompt = self.prompt(objective)
            return await self.engine.generate_async(user=self.prompter(user_prompt, data), system=system_prompt)
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
@register_objective_prompt("how_to_guide")
def how_to_guide():
    return """
        You specialize and are a master in explaining in detail how to accomplish a goal based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        You will give detailed, step by step instructions.
        Use numbers, bullets and other human readable formats to help with visualization.
    """


class AgentConfigRAG(RaiBaseAgent):
    def type(self): return "base"
    def parse(self, result): return result

async def main(name, user_prompt):
    # from rai.data.utilities.text_data import schedule_text
    results = await RaiBaseAgent.pipeline_async(
            name=name,
            user_prompt=user_prompt
        )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)

def mains(*names:str, user_prompt):
    # from rai.data.utilities.text_data import schedule_text
    results = RaiBaseAgent.pipelines(
            *names,
            user_prompt=user_prompt
        )
    print(user_prompt)
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
    user_prompt = "How do i register for placements?"
    mains("objective", "subject", user_prompt=user_prompt)
    # asyncio.run(
    #     main(
    #         name="objective",
    #         user_prompt=user_prompt
    #     )
    # )
    # asyncio.run(
    #     main(
    #         name="subject",
    #         user_prompt=user_prompt
    #     )
    # )