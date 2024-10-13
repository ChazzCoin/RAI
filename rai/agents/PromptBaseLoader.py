from abc import ABC, abstractmethod
from F.CLASS import Flass
import F

class PromptRegistry(ABC, Flass):
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
    def get_prompt_method(cls, category, method_name):
        if category not in cls._registry:
            raise ValueError(f"No prompts found for category '{category}'.")
        custom_methods = []
        for prompt_cls in cls._registry[category]:
            if hasattr(prompt_cls, method_name):
                method = getattr(prompt_cls(), method_name)
                return method
        if not custom_methods:
            raise ValueError(f"No method '{method_name}' found in category '{category}'.")
        return None
    @staticmethod
    def get(category, method_name, args=None):
        try:
            func = PromptRegistry.get_prompt_method(category, method_name)
            arg_type = PromptRegistry.get_func_type(func)
            if not args or arg_type == "none":
                return func()
            elif arg_type == "args":
                return func(*args)
            elif arg_type == "kwargs":
                return func(**args)
            else:
                return func(args)
        except Exception as e:
            print(f"There was an error running FairFunction. error=[ {e} ]")
    @staticmethod
    def get_func_type(func):
        sig = F.get_signature(func)
        sigStr = str(sig).replace("(", "").replace(")", "")
        t = F.convert_signature_arguments(sigStr)
        l = len(t)
        if l >= 2:
            return "args"
        elif F.is_kwargs(t):
            return "kwargs"
        elif not t or str(t) == '':
            return "none"
        else:
            return "single"
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

class SoccerPrompt(PromptRegistry, category="soccer"):
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


class MetadataPrompt(PromptRegistry, category="metadata"):
    def get_qa_training_formatter_prompt(self, role: str = ""): pass

    def get_context_expander_prompt(self, previous_messages=[]) -> str: pass

    def get_system_prompt(self, context: str = ""):
        return f"""
        !!GOLDEN RESPONSE RULE!!
        ->ONLY RETURN THE JSON METADATA OBJECT. NOTHING ELSE.<-
        ->DO NOT TO MODIFY MY METADATA OBJECT. VALIDATE MY MODEL MATCHES YOUR MODEL BEFORE YOU RESPOND TO ME.<-
        """
    def get_metadata_extraction_prompt(self, default_model:dict, content:str=""):
        return f"""
        You will read the following content and you will extract out the following metadata details.
        1. Look at each key name in the model and then try to determine the value for the key, based on the content.
        2. Extract keywords and some of the most important words used or the topic/category the text is about as tags.
        3. Only look for the model details.
        4. Return the exact metadata model I give you. Do not change anything.
        5. Try to guess the overall context and attempt to fill out all attributes even if you don't know.
        6. DO NOT MAKE UP NEW OR DIFFERENT ATTRIBUTES, just mold your response to fit my model no matter what!

        METADATA MODEL:
        {default_model}

        CONTENT:
        {content}

        RESPONSE RULES:
        1. ONLY RETURN THE JSON METADATA OBJECT AND THE ATTRIBUTES IVE GIVEN YOU.
        2. DO NOT MAKE UP ATTRIBUTES. Mold the reponse to fit my model.
        3. Verify your response model matches my metadata model PERFECTLY! 100%.
        
        If you send me a different metadata object model, you fucking failed me.
        """

class TrainingDataPrompt(PromptRegistry, category="training"):
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


class AutoFormatPrompt(PromptRegistry, category="autoformat"):
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
