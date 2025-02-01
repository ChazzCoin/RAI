from abc import ABC

from F import DICT, LIST

from rai.base.BaseAgents import RaiBaseAgent
from rai.assistant.connectors import RaiAi
from rai.data.utilities.TextUtils import TextProcessor
from rai.internal.connectors import VECTOR_DB_CLIENT
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


class RaiRagAgent(ABC, RaiAi, TextProcessor):
    name = None
    collections = [
        "pages",
        "summaries",
        "context_groups",
        "events",
        "images",
        "pdfs",
        "contacts",
        "locations"
    ]

    @classmethod
    async def pipeline_async(cls, prefix:str, user_prompt:str):
        agent_instance = cls()
        return await agent_instance.run_async(prefix=prefix, user_prompt=user_prompt)

    def system(self, name:str): return OBJECTIVE_PROMPT_REGISTRY.get(name)
    def user(self, user_prompt:str, data:str): return f"KNOWLEDGE LIBRARY:\n{data}\nUSER PROMPT:\n{user_prompt}"

    async def run_async(self, prefix:str, user_prompt:str):
        try:
            collection_list = [f"{prefix}.{c}" for c in self.collections]
            results = RaiBaseAgent.pipelines(
                "context_expander", "objective",
                user_prompt=user_prompt
            )

            # expanded_user_prompt = DICT.get("context_expander", results, user_prompt)
            wrapped_results = VECTOR_DB_CLIENT.queryThreaded(*collection_list, user_prompt=user_prompt, k=10)

            unwrapped_results = VECTOR_DB_CLIENT.unwrap_results(wrapped_results)
            query_results = VECTOR_DB_CLIENT.unwrap_formatted(unwrapped_results, k=5)

            objectives = DICT.get("objective", results, [])
            objective = LIST.get(0, objectives, "general")

            system_prompt = self.system(objective)
            ai_response = await self.engine.generate_async(user=self.user(user_prompt, query_results), system=system_prompt)
            final_response = f"{ai_response}"
            return final_response
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
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS AS HYPERLINKS WHEN APPROPRIATE**
    """

@register_objective_prompt("find_search")
def find_search():
    return """
        You specialize and are a master in extracting and returning concise and specific information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS WHEN APPROPRIATE**
    """
@register_objective_prompt("summarize")
def summarize():
    return """
        You specialize and are a master in summarizing a large set of information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS WHEN APPROPRIATE**
    """
@register_objective_prompt("explain")
def explain():
    return """
        You specialize and are a master in further explaining in more detail based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS WHEN APPROPRIATE**
    """
@register_objective_prompt("clarify")
def clarify():
    return """
        You specialize and are a master in clarifying information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS WHEN APPROPRIATE**
    """
@register_objective_prompt("create")
def create():
    return """
        You specialize and are a master in creating new content based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE SOURCES AND URLS, CONTACTS, EMAILS, ADDRESSES AND LOCATIONS WHEN APPROPRIATE**
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