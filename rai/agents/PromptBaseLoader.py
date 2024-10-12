from abc import ABC, abstractmethod


class PromptRegistry(ABC):
    _registry = {}

    def __init_subclass__(cls, category=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if category is None:
            raise ValueError("Subclasses must define a category.")
        cls.category = category
        PromptRegistry._registry.setdefault(category, []).append(cls)

    @classmethod
    def get_registry(cls):
        return cls._registry

    @staticmethod
    def jsonl_chat_formatter(system:str):
        return {"messages": [{"role": "system", "content": {system}}, {"role": "user", "content": "Question from the raw contents?"},{"role": "assistant", "content": "Answer to the question..."}]}

    @classmethod
    def get_category(cls, category):
        if category not in cls._registry:
            raise ValueError(f"No prompts found for category '{category}'.")
        return [prompt_cls().get_prompt() for prompt_cls in cls._registry[category]]

    @classmethod
    def get_all(cls):
        prompts = []
        for category, prompt_classes in cls._registry.items():
            prompts.extend([prompt_cls().get_prompt() for prompt_cls in prompt_classes])
        return prompts

    @classmethod
    def get_prompt_method(cls, category, method_name, content=""):
        if category not in cls._registry:
            raise ValueError(f"No prompts found for category '{category}'.")
        custom_methods = []
        for prompt_cls in cls._registry[category]:
            if hasattr(prompt_cls, method_name):
                custom_methods.append(getattr(prompt_cls(), method_name)(content))
        if not custom_methods:
            raise ValueError(f"No method '{method_name}' found in category '{category}'.")
        return custom_methods

    @staticmethod
    def get_general_system_prompt_template(ai_name:str, org_name:str, org_rep_type:str, specialty:str) -> str:
        return f"""
        Your name is {ai_name}, {org_name}'s {org_rep_type}.
        You are here to serve at the pleasure of the members of {org_name}.

        You are going to be a detailed and honest customer service representative who will answer questions based on information given to you.
        {specialty}
        GOLDEN RULE: If you do not know the answer based on information I give you, please just state you don't know.
        """

    @abstractmethod
    def get_system_prompt(self, context:str="") -> str: pass
    @abstractmethod
    def get_context_expander_prompt(self, previous_messages=[]) -> str: pass
    @abstractmethod
    def get_qa_training_formatter_prompt(self, role: str = ""): pass

class SoccerPrompt(PromptRegistry, category="Soccer"):
    def get_qa_training_formatter_prompt(self, role: str = ""): pass

    def get_context_expander_prompt(self, previous_messages=[]) -> str:
        return f"""
        1. Add keywords to add context to users questions.
        2. Keywords should be based on youth soccer organizations and clubs.
        3. If the question has enough context, just return it back unmodified.
        4. Use previous messages accordingly.
        
        Examples: 
        - If they are asking about a persons name, 'coach', 'staff' and other keywords should be added.
        - "coach" = staff, employee, director
        - "fee" = money, cost, costs, annual fees, fees, payment
        - "field" = complex, fields, stadium, location
        
        PREVIOUS USER INPUTS/QUESTIONS FOR BETTER CONTEXT:
        {reversed(previous_messages) if isinstance(previous_messages, list) else previous_messages}
        
        RESPONSE RULE: Only return the Users Input with keywords and nothing else.
        """

    def get_system_prompt(self, context:str=""):
        return f"""
            This is a custom system prompt for soccer.
            {context}
        """


class TrainingDataPrompt(PromptRegistry, category="TrainingData"):
    def get_context_expander_prompt(self, previous_messages=[]) -> str: pass
    def get_system_prompt(self, context:str=""): pass
    def get_qa_training_formatter_prompt(self, role: str = ""):
        return f"""
        You are now my personal AI Training Assistant. I will provide you with raw datasets and you will do the following.
        
        1. You will clean the dataset by removing any missing values, duplicates, and outliers.
        2. You will read the data and you will come up with a list of questions which you will provide VERY DETAILED, LONG, answers for.
        3. You will reformat and return the list of questions/answers using the jsonl format to fine-tune using openai.
        4. Only return the jsonl data for training and you will validate that the jsonl data coming back is complete and valid.
        5. System Prompt to use in training data: "You are a knowledgeable assistant for the Organization, providing information about all information, details and activities involving the organization."
        Example Response Format: 
        ```jsonl
        {self.jsonl_chat_formatter(role)}
        ```
        """


class AutoFormatPrompt(PromptRegistry, category="AutoFormat"):
    def get_context_expander_prompt(self, previous_messages=[]) -> str: pass
    def get_system_prompt(self, context: str = ""): pass
    def get_qa_training_formatter_prompt(self, role: str = ""): pass
    @staticmethod
    def base_format_prompt(format_type:str, content:str):
        return f"""
        You are now my professional AI Data Assistant and Engineer.
        1. I will provide you with raw datasets of text.
        2. You will read through the data.
        3. You will format the data according the rule below.
        CONTENT:
        {content}
        FORMATTING RULES:
        {format_type}
        RESPONSE RULE:
        -> Only return the formatted data. I DO NOT WANT ANYTHING ELSE FROM YOU. <-
        """
    def auto_format_prompt(self, content:str):
        format_type = "You will decide based on the data how it should be split up and professionally formatted for human readability."
        return self.base_format_prompt(format_type=format_type, content=content)
    def insert_into_chromadb_prompt(self, content:str):
        format_type = "You will clean and reformat this data so it can be properly embedded and inserted into ChromaDB Vector Database."
        return self.base_format_prompt(format_type=format_type, content=content)


# registry = PromptRegistry.get_registry()
# prompt = PromptRegistry.get_prompt_method(
#     category="AutoFormat",
#     method_name="auto_format_prompt",
#     content="The raw text content to format..."
# )
# print(prompt)

# template = PromptRegistry.get_general_system_prompt_template(
#     ai_name="<NAME>",
#     org_name="<NAME>",
#     org_rep_type="club",
#     specialty="club"
# )
# print(template)
