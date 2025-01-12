import types
from abc import abstractmethod, ABC

from F import DICT

from rai.assistant.connectors import RaiAi
from rai.assistant.models import RaiQueryExpander, RaiMetadata, ListOfQuestionAnswers, TrueOrFalse
from rai.data.utilities.TextUtils import TextProcessor

AGENT_REGISTRY = {}

AGENT_FUNCTIONS = {

}

AGENT_PROMPTS = {
    "default": lambda prompt="You are an helpful Assistant": prompt,
    "question_answer": """
        You will take the following dataset and you will generate accurate questions and corresponding answers.
        1. Questions: should be the most likely asked human questions based on the context of the information.
        2. Answers: should be detailed and as accurate as possible.
        Rule: If you do not know that answer, do not make something up. Just do not include that question and answer.
        """,
    "metadata": """
        You will read the following content and you will extract out the following metadata details for vector database and query optimizations.
        1. Look at each key name in the model and then try to determine the value for the key, based on the content.
        2. Try to guess the overall context and attempt to fill out all attributes even if you don't know.
        """,
    "true_false": """
        **You will take the following user request/query for RAG Chat and then answer the following question based on the query.**
        **You will only response with a True or False.**
        *Rule: If you do not know the answer, default to False.*
        """,
    "context_expander": lambda context="General": f"""
        **You will read the following User Query and add Proper context tag words to enhance vector RAG queries.**
        **User the following Topic/Category as contextual reference for enhancement.**
        **Only return the new query**
        CONTEXTUAL REFERENCE [ {context} ]
        """,
    "categorizer": lambda context="general": f"""
        **OVERALL PURPOSE**:
        Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
        **OVERALL CONTEXT**:
        {context}
        **OBJECTIVE**:
        - Treat each function name in the "functions" list as a Topic/Category.
        - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
        - Return the function calls (in a specific format) that match the user's needs.
        """,

}

def register_agent(name: str):
    def decorator(cls):
        """
        1. Registers `cls` under `name` in our registry.
        2. Returns `cls` unchanged.
        """
        AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator


class RaiBaseAgent(ABC, RaiAi, TextProcessor):
    name = None
    results = None
    json_obj_list:[] = None

    @classmethod
    def get_registry(cls):
        """Returns the entire registry dict."""
        return AGENT_REGISTRY

    @classmethod
    def pipeline(cls, name: str, user_prompt: str, system_prompt: str=None):
        """
        Main pipeline method. Looks up which agent classes are registered under 'name',
        instantiates the first one, and calls its 'run(...)' method.
        """
        agent_classes = AGENT_REGISTRY.get(name)
        if not agent_classes:
            raise ValueError(f"No agent found with name '{name}'")
        cls.name = name
        # You might decide to pick the first, or do additional logic if multiple classes are registered.
        agent_cls = agent_classes[0]

        # Instantiate the agent. If your agent requires, e.g. an engine, pass it here.
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt, system_prompt=system_prompt)

    @abstractmethod
    def format(self): pass
    @abstractmethod
    def functions(self): pass

    def system_prompt(self, system_prompt=""):
        prompt = DICT.get(self.name, AGENT_PROMPTS, None)
        if prompt is None:
            prompt = DICT.get("default", AGENT_PROMPTS, "You are a helpful assistant.")
        if type(prompt) in [types.LambdaType]:
            return prompt(system_prompt)
        else:
            return prompt

    def run(self, user_prompt=None, system_prompt=None):
        try:
            if self.format():
                return self.engine.generate_format(
                    user=self.format_dataset_to_string(user_prompt),
                    system=self.system_prompt(system_prompt),
                    format=self.format()
                )
            elif self.functions():
                return self.engine.generate_function(
                    user=self.format_dataset_to_string(user_prompt),
                    system=self.system_prompt(system_prompt),
                    functions=self.functions()
                )
            else:
                return self.engine.generate(
                    user=self.format_dataset_to_string(user_prompt),
                    system= self.system_prompt(system_prompt)
                )
        except Exception as e:
            print(f"Error: {e}")
            return None

@register_agent("categorizer")
class AgentConfigPrimaryCategorizer(RaiBaseAgent):
    def format(self): return None
    def functions(self): return None


"""
These seem to be turning into Configurations for agents.
What they do, how they do it...what they need...etc...
"""
@register_agent("context_expander")
class AgentConfigPromptExpander(RaiBaseAgent):
    def format(self): return RaiQueryExpander
    def functions(self): return None

@register_agent("metadata")
class AgentConfigMetadata(RaiBaseAgent):
    def format(self): return RaiMetadata
    def functions(self): return None

@register_agent("question_answer")
class AgentConfigQuestionAnswer(RaiBaseAgent):
    def format(self): return ListOfQuestionAnswers
    def functions(self): return None

@register_agent("true_false")
class AgentConfigTrueOrFalse(RaiBaseAgent):
    def format(self): return TrueOrFalse
    def functions(self): return None


if __name__ == "__main__":

    print(
        RaiBaseAgent.pipeline(
            name="true_false",
            user_prompt="Do we have game this week?",
            system_prompt="""
                **Is the user asking about a calendar or date based event?**
                *A practice, game, tournament, meeting, party, anything that might have a calendar based event.*
                """
        )
    )