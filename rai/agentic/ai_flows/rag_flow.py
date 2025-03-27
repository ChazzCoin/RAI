import threading
from abc import ABC, abstractmethod
from datetime import datetime
from F import DICT, LIST

from rai.agentic.ai_flows.r_flows import register_flow
from rai.agentic.ai_tasks.query_task import RaiQueryAgentResults, rQueryTask
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor
from rai.RAG.connectors import VECTOR_DB_CLIENT

OBJECTIVE_PROMPT_REGISTRY = {}
RAG_AGENT_REGISTRY = {}
def register_rag_agent(name: str):
    def decorator(cls):
        RAG_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator

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

@register_flow("rag")
class rRagFlow(ABC, rAI, TextProcessor):
    name = None
    first = []
    second = []
    third = []
    collections = {
        "pages": 1,
        "events": 2,
        "images": 3,
        "contacts": 2,
        "locations": 2,
        "agent": 1,
        "nlp": 3,
        "fnlp": 3,
        "agentnlp": 1
    }

    @classmethod
    def exec(cls, name: str, prefix: str, user_prompt: str):
        agent_classes = RAG_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(prefix=prefix, user_prompt=user_prompt)
    @classmethod
    def flow(cls, name: str, prefix: str, user_prompt: str):
        agent_classes = RAG_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(prefix=prefix, user_prompt=user_prompt)

    @classmethod
    async def flow_async(cls, name: str, prefix: str, user_prompt: str):
        agent_classes = RAG_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(prefix=prefix, user_prompt=user_prompt)
    @abstractmethod
    def run(self, prefix:str, user_prompt:str): pass
    @abstractmethod
    async def run_async(self, prefix:str, user_prompt:str): pass
    def system(self, name:str): return OBJECTIVE_PROMPT_REGISTRY.get(name)
    def user(self, user_prompt:str, data:str):
        return f"""
            KNOWLEDGE LIBRARY:
            {data}
            REAL-TIME DATA:
            {self.real_time_data()}
            USER PROMPT:
            {user_prompt}
        """
    @staticmethod
    def remove_text_before_last_period(text: str) -> str:
        if '.' not in text: return text
        return text.rsplit('.', 1)[-1]
    def get_first(self, key, obj, default):
        return LIST.get(0, DICT.get(key, obj, []), default)
    def unwrap_collection(self, name:str, results: {}) -> []:
        for k,v in results.items():
            if not v: continue
            tempK = self.remove_text_before_last_period(k)
            if tempK == name:
                return results[k]


    def unwrap_results(self, results: {}) -> []:
        unwrapped_results = []
        for k,v in results.items():
            if not v: continue
            tempK = self.remove_text_before_last_period(k)
            if self.collections[tempK] == 1:
                self.first.append(v)
            elif self.collections[tempK] == 2:
                self.second.append(v)
            elif self.collections[tempK] == 3:
                self.third.append(v)
            unwrapped_results.append(v)

        flat = LIST.flatten(unwrapped_results)
        sort_flat = sorted(flat, key=lambda x: x["distance"])
        return sort_flat
    def unwrap_first(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.first:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    def unwrap_second(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.second:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    def unwrap_third(self, k=5):
        unwrapped_results = []
        count = 1
        for i in self.third:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])
    @staticmethod
    def unwrap_formatted(results, k=5):
        unwrapped_results = []
        count = 1
        for i in results:
            formatted = DICT.get("formatted", i, "")
            metadata = DICT.get("metadata", i, "")
            unwrapped_results.append(f"\nDOCUMENT: {count}\n{formatted}\nMETADATA: {count}\n{metadata}")
        if len(unwrapped_results) <= k:
            return "\n".join(unwrapped_results)
        else:
            return "\n".join(unwrapped_results[:k])

    def filter_by_distance(self, objects: list[dict]) -> list[dict]:
        if not objects:
            return []

        # Sort the list by 'distance' in ascending order
        objects.sort(key=lambda x: x['distance'])

        # Get the top object's distance
        top_distance = objects[0]['distance']

        # Define the valid range
        min_distance = top_distance - 0.25
        max_distance = top_distance + 0.25

        # Filter objects within the valid range
        filtered_objects = [obj for obj in objects if min_distance <= obj['distance'] <= max_distance]

        return filtered_objects

    def real_time_data(self):
        now = datetime.now()
        return f"""
        Current Date & Time: {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}
        """
    def get_collections(self, prefix):
        return [f"{prefix}.{c}" for c in self.collections]
    def generate_rag_response(self, user_prompt:str, data, system_prompt:str):
        ai_response = self.engine.generate(user=self.user(user_prompt, data), system=system_prompt)
        final_response = f"{ai_response}"
        return final_response
    async def generate_rag_response_async(self, user_prompt:str, data, system_prompt:str):
        ai_response = await self.engine.generate_async(user=self.user(user_prompt, data), system=system_prompt)
        final_response = f"{ai_response}"
        return final_response


"""
pages = self.unwrap_collection('pages', wrapped_results)
events = self.unwrap_collection('events', wrapped_results)
top_only = self.filter_by_distance(unwrapped_results)
top_doc: RaiLoaderDocument = LIST.get(0, top_only, None)

top_doc_meta = DICT.get("metadata", top_doc, None)

top_parent_id = DICT.get("parent_id", top_doc_meta, None)
top_page_id = DICT.get("page_id", top_doc_meta, None)
top_page_number = DICT.get("page_number", top_doc_meta, None)
parent_where_query = { "parent_id": {"$eq": top_parent_id} }
page_where_query = { "page_id": {"$eq": top_page_id} }
number_where_query = { "page_number": {"$eq": top_page_number} }
where_results = VECTOR_DB_CLIENT.queryThreaded(*collection_list, user_prompt=user_prompt, k=10, where=page_where_query)

"""

@register_rag_agent("base")
class RagAgentBaseRunner(rRagFlow):
    def run(self, prefix: str, user_prompt: str) -> RaiQueryAgentResults:
        try:
            # self.switch_engine('ollama')
            results = rTextTools.tool(
                "objective",
                user_prompt=user_prompt
            )
            agent_results: RaiQueryAgentResults = rQueryTask.execute(self.name, prefix, user_prompt)

            objectives = DICT.get("objective", results, [])
            objective = LIST.get(0, objectives, "general")

            system_prompt = self.system(objective)
            # formatted = TextProcessor.clean_text_for_openai_embedding(agent_results.formatted)
            agent_results.response = self.generate_rag_response(user_prompt, agent_results.formatted, system_prompt)
            return agent_results
        except Exception as e:
            print(f"Error: {e}")
            return None
    async def run_async(self, prefix: str, user_prompt: str) -> RaiQueryAgentResults:
        try:
            # self.switch_engine('ollama')
            results = rTextTools.tools(
                "objective",
                user_prompt=user_prompt
            )

            agent_results: RaiQueryAgentResults = rQueryTask.execute(self.name, prefix, user_prompt)

            objectives = DICT.get("objective", results, [])
            objective = LIST.get(0, objectives, "general")

            system_prompt = self.system(objective)
            # formatted = TextProcessor.clean_text_for_openai_embedding(agent_results.formatted)
            agent_results.response = await self.generate_rag_response_async(user_prompt, agent_results.formatted, system_prompt)
            return agent_results
        except Exception as e:
            print(f"Error: {e}")
            return None
@register_rag_agent("breakdown")
class RagAgentBreakdownRunner(rRagFlow):
    async def run_async(self, prefix:str, user_prompt:str):
        try:
            collection_list = [f"{prefix}.{c}" for c in self.collections.keys()]
            context_prompt = "RaiBaseContexts.flow('soccer')"
            prompts = []
            responses = []
            is_question = await rTextTools.tool_async(
                name='is_true',
                user_prompt=user_prompt,
                system_prompt='Is the following User Prompt asking a Question?'
            )
            if is_question:
                each_question = await rTextTools.tool_async(
                    name='separate_prompt',
                    user_prompt=user_prompt
                )
                if each_question:
                    prompts = each_question
            else:
                prompts = [user_prompt]

            print(prompts)
            count = 1

            def thread_runner(prompt, user_prompt, context_prompt, count):
                results = rTextTools.tools(
                    "context_expander", "objective",
                    user_prompt=user_prompt,
                    system_prompt=context_prompt
                )

                response_objective = self.get_first("objective", results, "general")
                print("Prompt:", prompt)
                print("Objective:", response_objective)
                system_prompt = self.system(response_objective)

                prompt_expanded = DICT.get("context_expander", results, user_prompt)

                wrapped_results = VECTOR_DB_CLIENT.queries(*collection_list,
                                                           user_prompt=f"{prompt}\n{prompt_expanded}", k=10)
                unwrapped_results = self.unwrap_results(wrapped_results)
                query_results = self.unwrap_formatted(unwrapped_results, k=15)

                ai_response = self.engine.generate(user=self.user(prompt, query_results), system=system_prompt)
                prepped_reponse = f"\n{count}. {prompt}\n\n{ai_response}"
                responses.append(prepped_reponse)

            threads = []
            for prompt in prompts:
                thread = threading.Thread(target=thread_runner, args=(prompt, user_prompt, context_prompt, count))
                threads.append(thread)
                thread.start()
                count += 1
            for thread in threads:
                thread.join()

            final_response = "\n\n".join(responses)
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
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **BASED ON THE PROVIDED REAL-TIME DATE, PROVIDE WARNINGS FOR PAST DATES**
    """
@register_objective_prompt("find_search")
def find_search():
    return """
        You specialize and are a master in extracting and returning concise and specific information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **BASED ON THE PROVIDED REAL-TIME DATE, PROVIDE WARNINGS FOR PAST DATES**
    """
@register_objective_prompt("summarize")
def summarize():
    return """
        You specialize and are a master in summarizing a large set of information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **BASED ON THE PROVIDED REAL-TIME DATE, PROVIDE WARNINGS FOR PAST DATES**
    """
@register_objective_prompt("explain")
def explain():
    return """
        You specialize and are a master in further explaining in more detail based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **BASED ON THE PROVIDED REAL-TIME DATE, PROVIDE WARNINGS FOR PAST DATES**
    """
@register_objective_prompt("clarify")
def clarify():
    return """
        You specialize and are a master in clarifying information based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **BASED ON THE PROVIDED REAL-TIME DATE, PROVIDE WARNINGS FOR PAST DATES**
    """
@register_objective_prompt("create")
def create():
    return """
        You specialize and are a master in creating new content based on the information provided.
        You will read the given knowledge library of documents and break down how to accomplish the users prompt.
        **ALWAYS INCLUDE HUMAN READABLE LINKS FOR SOURCES AND URLS, CONTACTS, EMAILS**
        **ALWAYS INCLUDE ADDRESSES AND LOCATIONS WITH GOOGLE URL LINKS**
        **ALWAYS BE DATE/TIME AWARE AND INCLUDE WARNINGS FOR OLD/PAST DATES**
    """

class AgentConfigRAG(rTextTools):
    def type(self): return "base"
    def parse(self, result): return result

def mains(name:str, prefix, user_prompt):
    # from rai.pipeline.utilities.text_data import schedule_text
    results = rRagFlow.flow(
            name=name,
            prefix=prefix,
            user_prompt=user_prompt
        )
    print(user_prompt)
    if type(results) in [RaiQueryAgentResults]:
        print(results.response)
    elif type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)

if __name__ == "__main__":
    user_prompt = "What can you tell me about alexus edwards?"
    mains("base", "referral2025.1", user_prompt=user_prompt)
