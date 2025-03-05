import json

from rai.agentic.ai_plugins.redis_state import PluginState
from rai.assistant.connectors import rAI

SYSTEM_PROMPT = """
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

# The main agent class that implements the operation workflow.
class MedicalOperationAgent:
    # Define required data for each state.
    REQUIRED_DATA = {
        "preoperative_timeout": [
            "surgeon",
            "patient",
            "procedure",
            "side_of_surgery",
            "preoperative_medications_given"
        ],
        "postoperative_signout": [
            "procedure_performed",
            "pathology_specimen"
        ]
    }

    def __init__(self, session_id: str):
        """
        Initialize the agent with a unique session ID.
        This sets up a namespaced Redis state and initializes the state and data storage.
        """
        self.session_id = session_id
        self.state_storage = PluginState(state_namespace=session_id)
        # Initialize current state if not already set.
        if not self.state_storage.get_state("current_state"):
            self.state_storage.set_state("current_state", "preoperative_timeout")
        # Initialize operation data storage if not set.
        if not self.state_storage.get_state("operation_data"):
            self.state_storage.set_state("operation_data", {})

    def get_current_state(self) -> str:
        """
        Retrieve the current state from Redis.
        """
        return self.state_storage.get_state("current_state")

    def set_current_state(self, new_state: str):
        """
        Update the current state in Redis.
        """
        self.state_storage.set_state("current_state", new_state)

    def get_operation_data(self) -> dict:
        """
        Retrieve the operation data (all user-provided values) from Redis.
        """
        data = self.state_storage.get_state("operation_data")
        return data if data else {}

    def update_operation_data(self, new_data: dict):
        """
        Update the operation data with new key/value pairs.
        """
        data = self.get_operation_data()
        data.update(new_data)
        self.state_storage.set_state("operation_data", data)

    def prompt_for_missing_data(self, key: str) -> str:
        """
        Placeholder for prompting the user for missing data.
        In a production environment, this might be replaced with a UI prompt or an API call.
        """
        # For now, use the built-in input function.
        return input(f"Please provide the required data for '{key}': ")

    def check_required_data(self, state: str):
        """
        Check if all required data for the current state is present.
        If any required keys are missing, prompt the user for them.
        """
        required_keys = self.REQUIRED_DATA.get(state, [])
        data = self.get_operation_data()
        missing_keys = [key for key in required_keys if key not in data or data[key] is None]

        for key in missing_keys:
            # Prompt the user until valid data is provided.
            user_value = self.prompt_for_missing_data(key)
            data[key] = user_value

        self.state_storage.set_state("operation_data", data)

    def call_ai(self, prompt: str) -> str:
        """
        Placeholder function for calling your custom AI generation.
        Replace this function with your AI integration.
        """
        # Example: return custom_ai_generate(prompt)
        return rAI('openai').generate(user=prompt, system=SYSTEM_PROMPT)

    def run_preoperative_timeout(self, user_prompt: str = None):
        """
        Run the preoperative timeout workflow:
        1. Ensure all required preoperative data is available.
        2. Construct a prompt for AI generation, optionally incorporating a user prompt.
        3. Call the AI generation placeholder.
        4. Transition to the next state.
        """
        print("Starting Preoperative Timeout...")
        self.check_required_data("preoperative_timeout")

        operation_data = self.get_operation_data()
        # Use the user_prompt if provided, otherwise default text.
        if user_prompt:
            prompt = f"{user_prompt}\nPreoperative Timeout Data: {operation_data}"
        else:
            prompt = f"Preoperative Timeout: Confirm the following details: {operation_data}"

        result = self.call_ai(prompt)
        print("Preoperative Timeout Completed. AI response:", result)

        # Transition to the next state.
        self.set_current_state("postoperative_signout")

    def run_postoperative_signout(self, user_prompt: str = None):
        """
        Run the postoperative sign out workflow:
        1. Ensure all required postprocedure data is available.
        2. Construct a prompt for AI generation, optionally incorporating a user prompt.
        3. Call the AI generation placeholder.
        4. Mark the workflow as complete.
        """
        print("Starting Postoperative Sign Out...")
        self.check_required_data("postoperative_signout")

        operation_data = self.get_operation_data()
        if user_prompt:
            prompt = f"{user_prompt}\nPostoperative Sign Out Data: {operation_data}"
        else:
            prompt = f"Postoperative Sign Out: Confirm the following details: {operation_data}"

        result = self.call_ai(prompt)
        print("Postoperative Sign Out Completed. AI response:", result)

        # Mark the workflow as complete.
        self.set_current_state("completed")

    def process_current_state(self, user_prompt: str = None):
        """
        Check the current state and dispatch the corresponding state method.
        If a user_prompt is provided, it is passed along to the state method.
        """
        current_state = self.get_current_state()
        if current_state == "preoperative_timeout":
            self.run_preoperative_timeout(user_prompt)
        elif current_state == "postoperative_signout":
            self.run_postoperative_signout(user_prompt)
        elif current_state == "completed":
            print("Operation workflow is complete.")
        else:
            print(f"Unknown state: {current_state}")

    def run(self, user_prompt: str = None):
        """
        Main loop to process the operation workflow until it is complete.
        An optional user_prompt can be provided to influence the AI prompt in each state.
        """
        while self.get_current_state() != "completed":
            self.process_current_state(user_prompt)
        print("All steps completed.")


# Example usage:
if __name__ == "__main__":
    session_id = "session_12345"  # This should be unique for each session
    # Optionally pass in a custom prompt to drive the workflow.
    custom_prompt = "Surgeon is Dr. Andrew Romeo"
    agent = MedicalOperationAgent(session_id)
    agent.run(user_prompt=custom_prompt)
