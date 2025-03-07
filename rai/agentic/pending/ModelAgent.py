from abc import ABC, abstractmethod
from typing import List, Dict

from pydantic import BaseModel

from rai.agentic.ai_plugins.QCache import VectorCache
from rai.agentic.ai_plugins.QStore import VectorStore
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor

MODEL_AGENT_REGISTRY = {}
def register_model_agent(name: str):
    def decorator(cls):
        MODEL_AGENT_REGISTRY.setdefault(name, []).append(cls)
        return cls

    return decorator


NORA = """

-> System Prompt
You are an operating room assistant named Nora. 
Your job is to perform a preoperative time out and a postoperative sign out. 



**CONFIRM the following information for timeout and signout.**

**USE THE BELOW INFORMATION about each surgeon and procedure to confirm any additional features necessary.**


DATA NEEDED:
Preprocedure Timeout:
    Confirm Surgeon
    Confirm Patient
    Confirm Procedure
    Confirm Side of Surgery
    Confirm preoperative medications given
    Postprocedure Sign Out:
    Confirm Procedure performed
    Confirm presence of pathology specimen

Surgeons:
    Dr. Andrew Romeo
    Dr. Jai Thakur
    Microscope chair
    Number 2 kerrisons for craniotomy
    Dr. Rich Menger

Procedures:
    Craniotomy for Epilepsy
        • Usually has pathology specimen
        • Neuropace placement needs rep present

Deep Brain Stimulation Lead Placement
    • Confirm Side
    • Confirm company
    • Confirm target
    • Confirm targeting system
    • Confirm nexframe array

Deep Brain Stimulation Battery Initial Placement
    • Confirm side
    • Confirm battery type

Deep Brain Stimulator Battery Replacement
    • Confirm side
    • Confirm battery type

Stereotactic Depth Electrode Placement
    • Confirm side
    • Need Electrode rep and Globus rep present

Hypoglossal Nerve Stimulator Placement
    • No paralytic, Motor monitoring performed

1. Craniotomy for Tumor resection
    • Both frozen and permanent pathology specimens
    • Need sonopet
    • Need microscope
    • Need number 2 kerrison if Dr. Thakur

2. Endoscopic Endonasal Tumor resection
    • Both frozen and permanent pathology specimens

3. Ventriculoperitoneal shunt placement
    • General surgery for laparoscopic assistance
    • Confirm valve type and setting
    • Confirm availability of antibiotic impregnated catheters
"""



class RaiModelAgent(ABC, rAI, TextProcessor):
    name = None

    store = VectorStore()
    cache = VectorCache()


    @classmethod
    def execute(cls, name: str, user_prompt: str):
        agent_classes = MODEL_AGENT_REGISTRY.get(name)
        if not agent_classes: return None
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt)
    @abstractmethod
    def run(self, user_prompt:str): pass
    @abstractmethod
    def functions(self) -> dict: pass
    @staticmethod
    def getFunctionJsonNoArgs(name, description) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description
            },
        }
    def setup_fuctions(self):
        return [ self.getFunctionJsonNoArgs(key, value) for key, value in self.functions().items() ]

    def get_system_prompt_from_cache(self):
        return self.cache.get_key(key=f'model:system_prompt:{self.name}')

    def save_system_prompt_to_cache(self, system_prompt:str):
        return self.cache.set_key(key=f'model:system_prompt:{self.name}', value=system_prompt)

    def get_new_prompt_question_from_cache(self):
        return self.cache.get_key(key=f'model:new_prompt_question:{self.name}')

    def save_new_prompt_question_to_cache(self, value:bool):
        return self.cache.set_key(key=f'model:new_prompt_question:{self.name}', value=str(value))

    def get_enter_new_prompt_from_cache(self):
        return self.cache.get_key(key=f'model:enter_new_prompt:{self.name}')

    def save_enter_new_prompt_to_cache(self, value:bool):
        return self.cache.set_key(key=f'model:enter_new_prompt:{self.name}', value=str(value))


class RaiModelAgentConfig(BaseModel):
    name: str
    user_prompt: str
    system_prompt: List[dict]
    ollama: str
    openai: str

@register_model_agent("base")
class ModelAgentBaseRunner(RaiModelAgent):
    def run(self, user_prompt: str):
        try:
            pass
        except Exception as e:
            print(f"Error: {e}")
            return None

@register_model_agent("cache")
class ModelAgentCacheRunner(RaiModelAgent):
    """

    -  Define the list of functions and what actions they make.
    - Each action needs to have a set of instructions or commands it utilizes.
    - Agents have their own functions and command utils..

    """
    def user_confirms(self, user_prompt) -> bool:
        return rTextTools.tool(
            name='is_true',
            user_prompt=user_prompt,
            system_prompt='Is the user prompt saying yes, agreeing, confirming or wanting to proceed forward?'
        )
    def user_wants_to_edit(self, user_prompt) -> bool:
        return rTextTools.tool(
            name='is_true',
            user_prompt=user_prompt,
            system_prompt='Is the user prompt asking to reset, update or change something?'
        )

    def states(self) -> Dict[str:str]:
        return  {
            "init": "User Prompt ",
            "check_prompt": "User Prompt ",
            "ask_new_prompt": "Okay! Go ahead and enter the new system prompt for the Agent please...",
            "confirm_new_prompt": "Okay! New Agent System Prompt has been saved!",
            "ready": "Agent is ready.",
            "error": "Agent is having an error.",
        }
    def questions(self) -> Dict[str:str]:
        return {
            "ask_new_prompt": "User Prompt ",
        }
    def actions(self) -> dict:
        return {
            "init": "User Prompt ",
        }
    def run(self, user_prompt: str):
        try:

            enter_new_prompt_requested = self.get_enter_new_prompt_from_cache()
            if enter_new_prompt_requested == 'True':
                self.save_system_prompt_to_cache(user_prompt)
                self.save_new_prompt_question_to_cache(False)
                self.save_enter_new_prompt_to_cache(False)
                return "Okay! New Agent System Prompt has been saved!"
            new_prompt_question_asked = self.get_new_prompt_question_from_cache()
            if new_prompt_question_asked == 'True':
                if self.user_confirms(user_prompt):
                    self.save_new_prompt_question_to_cache(False)
                    self.save_enter_new_prompt_to_cache(True)
                    return "Okay! Go ahead and enter the new system prompt for the Agent please..."

            if self.user_wants_to_edit(user_prompt):
                self.save_new_prompt_question_to_cache(False)
                self.save_enter_new_prompt_to_cache(True)
                return "Okay! Go ahead and enter the new system prompt for the Agent please..."

            cached_system_prompt = self.get_system_prompt_from_cache()
            if not cached_system_prompt:
                # ask user if they want to create a new prompt.
                self.save_new_prompt_question_to_cache(True)
                self.save_enter_new_prompt_to_cache(False)
                return "Uh oh! No Agent Found! Would you like to add one?"

            self.save_new_prompt_question_to_cache(False)
            self.save_enter_new_prompt_to_cache(False)
            return self.tool(user_prompt, cached_system_prompt)
        except Exception as e:
            print(f"Error: {e}")
            return None


if __name__ == "__main__":
    q = "Who is joel person?"
    results = RaiModelAgent.execute('cache', "Who are you?")
    print("\n-------------\n")
    print(results)
    print("\n-------------\n")