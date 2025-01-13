from abc import abstractmethod, ABC

from F import DICT

from rai.assistant.connectors import RaiAi
from rai.base.BaseFormats import RaiBaseFormats
from rai.base.BaseFunctions import RaiBaseFunctions
from rai.base.BasePrompts import RaiBasePrompts
from rai.data.utilities.TextUtils import TextProcessor

AGENT_REGISTRY = {}

# AAGENT_PROMPTS = {
#     "default": "You are an helpful Assistant",
#     "question_answer": """
#         You will take the following dataset and you will generate accurate questions and corresponding answers.
#         1. Questions: should be the most likely asked human questions based on the context of the information.
#         2. Answers: should be detailed and as accurate as possible.
#         Rule: If you do not know that answer, do not make something up. Just do not include that question and answer.
#         """,
#     "metadata": """
#         You will read the following content and you will extract out the following metadata details for vector database and query optimizations.
#         1. Look at each key name in the model and then try to determine the value for the key, based on the content.
#         2. Try to guess the overall context and attempt to fill out all attributes even if you don't know.
#         """,
#     "true_false": """
#         You are an AI assistant that strictly returns the Boolean truth value of a given statement—no additional text or commentary.
#         **Only respond with the single word "True" or "False".**
#         """,
#     "context_expander": f"""
#         **You will read the following User Query and add Proper context tag words to enhance vector RAG queries.**
#         **User the following Topic/Category as contextual reference for enhancement.**
#         **Only return the new query**
#         """,
#     "categorizer": f"""
#         **OVERALL PURPOSE**:
#         Your goal is to identify relevant function calls from the provided function definitions ("functions") based on the user's prompt.
#         **OBJECTIVE**:
#         - Treat each function name in the "functions" list as a Topic/Category.
#         - Thoroughly analyze the user's prompt to decide which function(s) apply (there may be more than one).
#         - Return the function calls (in a specific format) that match the user's needs.
#         """,
#
# }
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
        """
        1. Registers `cls` under `name` in our registry.
        2. Returns `cls` unchanged.
        """
        AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


class RaiBaseAgent(ABC, RaiAi, TextProcessor):
    name = None

    @classmethod
    def get_registry(cls): return AGENT_REGISTRY

    @classmethod
    def pipeline(cls, name: str, user_prompt: str, sub=False):
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
        return agent_instance.run(user_prompt=user_prompt, sub=sub)

    @abstractmethod
    def type(self): pass

    def prompt(self): return RaiBasePrompts.prompt(self.name)
    def agent_context(self): return DICT.get(self.name, CONTEXTS, {})
    def system_prompt(self):
        temp = self.prompt()
        if temp:
            return temp
        return DICT.get("prompt", self.agent_context())
    def context(self): return DICT.get("context", self.agent_context(), "")
    def prompter(self, user_prompt): return f"USER PROMPT:\n{user_prompt}\n{self.context()}"

    def run(self, user_prompt, sub=False):
        try:
            if self.type() == "format":
                return self.engine.generate_format(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt(),
                    format=RaiBaseFormats.pipeline(self.name)
                )
            elif self.type() == "function":
                return self.engine.generate_function(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt(),
                    functions=RaiBaseFunctions.pipeline(self.name, sub=sub)
                )
            elif self.type() == "base":
                return self.engine.generate(
                    user=self.prompter(user_prompt),
                    system=self.system_prompt()
                )
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
@register_agent("categorize_sports")
class AgentConfigPrimaryCategorizer(RaiBaseAgent):
    def type(self): return "function"

@register_agent("context_expander")
class AgentConfigPromptExpander(RaiBaseAgent):
    def type(self): return "format"

@register_agent("metadata")
class AgentConfigMetadata(RaiBaseAgent):
    def type(self): return "format"

@register_agent("faq")
class AgentConfigQuestionAnswer(RaiBaseAgent):
    def type(self): return "format"

@register_agent("is_event")
class AgentConfigTrueOrFalse(RaiBaseAgent):
    def type(self): return "format"

if __name__ == "__main__":
    from rai.data.utilities.text_data import book_text
    print(
        RaiBaseAgent.pipeline(
            name="faq",
            user_prompt=book_text
        )
    )

