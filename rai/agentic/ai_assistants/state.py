from rai.agentic.ai_plugins.assistant import rAssistantPlugin, rAssistantWithChainOfStepsPlugin
import json
from typing import List, Dict



class StateAssistant(rAssistantWithChainOfStepsPlugin):
    """
    A robust, stateless state manager for handling agent flows with Redis as the sole source of truth.
    All methods are static so that no class instance is required; every operation loads, modifies, and
    saves state directly to Redis.
    """

    def context(self) -> str:
        return """
        You will already have state_id.
        IF load_state is NONE or EMPTY: create_new_state
        DEFAULT STATE should be: 'started'
        IF data is required: generate_prompt_for_missing
        IF NO data is required: attempt_to_proceed_forward
        LAST STEP SHOULD ALWAYS BE EITHER
         1. attempt_to_proceed_forward
         2. generate_prompt_for_missing
        """

    @classmethod
    def request(cls, user_prompt:str, **attached_data):
        return cls().decide_and_call(user_request=user_prompt, **attached_data)

    @staticmethod
    def create_new_state(state_id:str, state_name: str, required_fields: List[str]) -> str:
        """
        Initialize a new state and store it in Redis.

        :param state_name: Name of the state.
        :param required_fields: List of required fields for this state.
        :param state_id: Optional unique identifier; if not provided, a slugified state name is used.
        :return: A success message including the state_id.
        """
        state_id = state_id if state_id else state_name.replace(" ", "_").lower()
        state_dict = {
            "state_name": state_name,
            "required_fields": required_fields,
            "data": {},
            "status": "created"
        }
        key = f"agent_state:{state_id}"
        StateAssistant.rRedis().set(key, json.dumps(state_dict))
        out = f"create_new_state: New state created with state_id '{state_id}' \n {state_dict}."
        StateAssistant.log_to_chain(out)
        return out

    @staticmethod
    def load_state(state_id: str) -> Dict:
        """Load the state from Redis."""
        key = f"agent_state:{state_id}"
        state_str = StateAssistant.rRedis().get(key)
        out = f"load_state: State has been loaded. [ Session key '{key}' ] [ {state_str} ]"
        StateAssistant.log_to_chain(out)
        if state_str: return json.loads(state_str)
        return {}

    @staticmethod
    def save_state(state_id: str, state: Dict) -> str:
        """Persist the state to Redis."""
        key = f"agent_state:{state_id}"
        StateAssistant.rRedis().set(key, json.dumps(state))
        out = f"save_state: State has been saved. [ Session key '{key}' ]"
        StateAssistant.log_to_chain(out)
        return out


    @staticmethod
    def is_complete(state_id: str) -> bool:
        """Check if all required fields for the given state have been provided."""
        state = StateAssistant.load_state(state_id)
        data = state.get("data", {})
        required_fields = state.get("required_fields", [])
        out = f"is_complete: {required_fields}"
        StateAssistant.log_to_chain(out)
        return all(field in data and data[field] is not None for field in required_fields)

    @staticmethod
    def missing_fields(state_id: str) -> List[str]:
        """Retrieve a list of required fields that are missing data for the given state."""
        state = StateAssistant.load_state(state_id)
        data = state.get("data", {})
        required_fields = state.get("required_fields", "[]")
        parsed_fields = json.loads(required_fields.replace("\'", "\""))
        result = [field for field in parsed_fields if field not in data or data[field] is None]
        out = "missing_fields: '{}'".format(", ".join(result))
        StateAssistant.log_to_chain(out)
        return result

    @staticmethod
    def attach_data(state_id: str, field: str, value: str) -> str:
        """Attach data to a specific field for the given state."""
        state = StateAssistant.load_state(state_id)
        if not state:
            out = f"No state found with state_id '{state_id}'."
            StateAssistant.log_to_chain(out)
            return out
        if field not in state.get("required_fields", []):
            out = f"Field '{field}' is not a valid required field for state '{state.get('state_name')}'."
            StateAssistant.log_to_chain(out)
            return out

        # Update data for the field.
        data = state.get("data", {})
        data[field] = value
        state["data"] = data

        # Update status based on completeness.
        if all(f in data and data[f] is not None for f in state.get("required_fields", [])):
            state["status"] = "completed"
        else:
            state["status"] = "in_progress"

        StateAssistant.save_state(state_id, state)
        out = f"Data for field '{field}' attached."
        StateAssistant.log_to_chain(out)
        return out

    @staticmethod
    def update_required_fields(state_id: str, new_required_fields: List[str]) -> str:
        """Update the required_fields of the state with the given state_id."""
        state = StateAssistant.load_state(state_id)
        if not state:
            out = f"No state found with state_id '{state_id}'."
            StateAssistant.log_to_chain(out)
            return out

        state["required_fields"] = new_required_fields
        data = state.get("data", {})
        # Update the status based on whether all new required fields have corresponding non-None data.
        if all(field in data and data[field] is not None for field in new_required_fields):
            state["status"] = "completed"
        else:
            state["status"] = "in_progress"

        StateAssistant.save_state(state_id, state)
        out = f"update_required_fields: Required fields updated to {new_required_fields} for state_id '{state_id}'."
        StateAssistant.log_to_chain(out)
        return out

    @staticmethod
    def generate_prompt_for_missing(state_id: str) -> str:
        """Generate a prompt listing the missing required data for the given state."""
        state = StateAssistant.load_state(state_id)
        if not state:
            return "No state found!"
        missing = StateAssistant.missing_fields(state_id)
        state_name = state.get("state_name", "")
        if missing:
            out = f"Please provide the following data for state '{state_name}': {str(missing)}."
            StateAssistant.log_to_chain(out)
            return out
        else:
            out = f"All required data has been provided for state '{state_name}'."
            StateAssistant.log_to_chain(out)
            return out

    @staticmethod
    def attempt_to_proceed_forward(state_id: str) -> str:
        """Attempt to proceed to the next state by checking for completeness."""
        state = StateAssistant.load_state(state_id)
        if not state:
            out = f"No state found with state_id '{state_id}'."
            StateAssistant.log_to_chain(out)
            return out

        if all(field in state.get("data", {}) and state["data"][field] is not None
               for field in state.get("required_fields", [])):
            state["status"] = "completed"
            StateAssistant.save_state(state_id, state)
            out = f"State '{state.get('state_name')}' is complete. Proceeding to next state..."
            StateAssistant.log_to_chain(out)
            return out
        else:
            # Update status to in_progress if any data exists.
            if any(field in state.get("data", {}) for field in state.get("required_fields", [])):
                state["status"] = "in_progress"
                StateAssistant.save_state(state_id, state)
            out = StateAssistant.generate_prompt_for_missing(state_id)
            StateAssistant.log_to_chain(out)
            return out

if __name__ == "__main__":
    # Define a sample state with required fields
    state_name = "Deep Brain Stimulation Lead Placement"
    required_fields = [
        "side",
        "company",
        "target",
        "targeting",
        "nexframe"
    ]

    # Initialize the state manager
    # state_manager = AgentStateManager()
    result = StateAssistant.request("Where do I stand currently?", state_id="raiko2")
    print(result)
    # state_manager.create_new_state(state_name, required_fields)
    #
    # # Optionally load an existing state from Redis
    # state_manager.load_state()
    #
    # # Check if all data is provided and attempt to proceed
    # print(state_manager.attempt_to_proceed_forward())
    #
    # # Attach data as it becomes available
    # state_manager.attach_data("Confirm Side", "Left")
    # state_manager.attach_data("Confirm company", "MedTech Inc.")
    #
    # # Re-check state completeness
    # print(state_manager.attempt_to_proceed_forward())