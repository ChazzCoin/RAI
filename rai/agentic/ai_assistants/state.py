
from rai.agentic.ai_plugins.assistant import rAssistantReasoningPlugin
import json
from typing import Any, Dict, Optional, Type, Union, List
from pydantic import BaseModel, Field

class StateAssistant(rAssistantReasoningPlugin):
    """
    A robust, stateless state manager for handling agent flows with Redis as the sole source of truth.
    All methods are static so that no class instance is required; every operation loads, modifies, and
    saves state directly to Redis.
    """

    class StateObject(BaseModel):
        state_id: str
        state_name: str
        required_fields: Dict[str, str] = Field(default_factory=dict)
        status: str = "started"

    @staticmethod
    def required_model() -> Type[BaseModel]:
        return StateAssistant.StateObject

    @staticmethod
    def assistant_rules() -> str:
        return """
        You will already have state_id.
        IF load_state is NONE or EMPTY: create_new_state
        DEFAULT STATE should be: 'started'
        IF required_fields data is missing: generate_prompt_for_missing
        IF all required_fields have data: attempt_to_proceed_forward
        LAST STEP SHOULD ALWAYS BE EITHER
         1. attempt_to_proceed_forward
         2. generate_prompt_for_missing
        """

    @classmethod
    def request(cls, user_prompt: str, **attached_data):
        return cls().reason(user_request=user_prompt, **attached_data)

    @staticmethod
    def _get_redis_key(state_id: str) -> str:
        return f"agent_state:{state_id}"

    @staticmethod
    def create_new_state(state_id: Optional[str], state_name: str, required_fields: Union[str, Dict[str, str]]) -> str:
        """
        Initialize a new state and store it in Redis.
        :param state_id: Optional unique identifier; if not provided, a slugified state name is used.
        :param state_name: Name of the state.
        :param required_fields: Either a dict mapping field names to initial data or a JSON string representing that dict.
        :return: A success message including the state_id.
        """
        state_id = state_id or state_name.replace(" ", "_").lower()
        if StateAssistant.get_state(state_id):
            return StateAssistant.assistant_log(f"State with state_id '{state_id}' already exists.")

        # If required_fields is a string, attempt to parse it as JSON.
        if isinstance(required_fields, str):
            try:
                required_fields = json.loads(required_fields)
            except Exception as e:
                return StateAssistant.assistant_log(f"Invalid required_fields JSON string: {e}")

        new_state = StateAssistant.StateObject(
            state_id=state_id,
            state_name=state_name,
            required_fields=required_fields,
            status="started"
        )
        key = StateAssistant._get_redis_key(state_id)
        StateAssistant.rRedis().set(key, json.dumps(new_state.dict()))
        return StateAssistant.assistant_log(
            f"create_new_state: New state created with state_id '{state_id}': {new_state.dict()}"
        )

    @staticmethod
    def get_state(state_id: str) -> Optional["StateObject"]:
        """Retrieve and parse the state from Redis into a StateObject."""
        key = StateAssistant._get_redis_key(state_id)
        state_str = StateAssistant.rRedis().get(key)
        StateAssistant.assistant_log(f"Retrieving state for key: '{key}', data: {state_str}")
        if not state_str:
            StateAssistant.assistant_log(f"No state found for key: '{key}'")
            return None
        try:
            state_data = json.loads(state_str)
            return StateAssistant.StateObject.parse_obj(state_data)
        except Exception as e:
            StateAssistant.assistant_log(f"Error parsing state data for key '{key}': {e}")
            return None

    @staticmethod
    def delete_state(state_id: str) -> str:
        """Delete the state from Redis."""
        key = StateAssistant._get_redis_key(state_id)
        try:
            response = StateAssistant.rRedis().delete(key)
            return StateAssistant.assistant_log(f"Deleted state with key '{key}'. Redis response: {response}")
        except Exception as e:
            return StateAssistant.assistant_log(f"Error deleting state with key '{key}': {e}")

    @staticmethod
    def _save_state_model(state_model: "StateObject") -> None:
        """Persist the StateObject model to Redis."""
        key = StateAssistant._get_redis_key(state_model.state_id)
        StateAssistant.rRedis().set(key, json.dumps(state_model.dict()))
        StateAssistant.assistant_log(f"State saved for key '{key}'.")

    @staticmethod
    def save_state(state: Union["StateObject", dict]) -> str:
        """
        Save the state to Redis. Accepts either a StateObject instance or a dictionary.
        """
        if isinstance(state, dict):
            try:
                state = StateAssistant.StateObject.parse_obj(state)
            except Exception as e:
                return StateAssistant.assistant_log(f"Error converting dict to StateObject: {e}")
        StateAssistant._save_state_model(state)
        return StateAssistant.assistant_log(f"State with state_id '{state.state_id}' saved.")

    @staticmethod
    def is_complete(state_id: str) -> bool:
        """
        Check if all required fields have been provided with non-empty values.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            return False
        return all(value is not None and value != "" for value in state.required_fields.values())

    @staticmethod
    def missing_fields(state_id: str) -> List[str]:
        """
        Retrieve a list of required fields that have missing or empty data.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            StateAssistant.assistant_log(f"No state found for state_id '{state_id}' to check missing fields.")
            return []
        missing = [field for field, value in state.required_fields.items() if not value]
        StateAssistant.assistant_log(f"Missing fields for state '{state.state_name}': {missing}")
        return missing

    @staticmethod
    def attach_data(state_id: str, field: str, value: str) -> str:
        """
        Attach data to a specific field in required_fields and update the state status accordingly.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            return StateAssistant.assistant_log(f"No state found with state_id '{state_id}'.")
        if field not in state.required_fields:
            return StateAssistant.assistant_log(f"Field '{field}' is not valid for state '{state.state_name}'.")
        state.required_fields[field] = value

        # Update state status based on completeness.
        if all(v is not None and v != "" for v in state.required_fields.values()):
            state.status = "completed"
        else:
            state.status = "in_progress"
        StateAssistant._save_state_model(state)
        return StateAssistant.assistant_log(f"Data for field '{field}' attached in state '{state.state_name}'.")

    @staticmethod
    def update_required_fields(state_id: str, new_required_fields: Union[str, Dict[str, str]]) -> str:
        """
        Update the required_fields dictionary for the state and recalculate completeness.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            return StateAssistant.assistant_log(f"No state found with state_id '{state_id}'.")

        # If new_required_fields is a string, parse it as JSON.
        if isinstance(new_required_fields, str):
            try:
                new_required_fields = json.loads(new_required_fields)
            except Exception as e:
                return StateAssistant.assistant_log(f"Invalid new_required_fields JSON string: {e}")

        state.required_fields = new_required_fields
        if all(v is not None and v != "" for v in new_required_fields.values()):
            state.status = "completed"
        else:
            state.status = "in_progress"
        StateAssistant._save_state_model(state)
        return StateAssistant.assistant_log(
            f"update_required_fields: Required fields updated to {new_required_fields} for state '{state.state_name}'."
        )

    @staticmethod
    def generate_prompt_for_missing(state_id: str) -> str:
        """
        Generate a prompt listing the missing required data for the state.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            return "No state found!"
        missing = StateAssistant.missing_fields(state_id)
        if missing:
            return StateAssistant.assistant_log(
                f"Please provide the following data for state '{state.state_name}': {missing}."
            )
        else:
            return StateAssistant.assistant_log(
                f"All required data has been provided for state '{state.state_name}'."
            )

    @staticmethod
    def attempt_to_proceed_forward(state_id: str) -> str:
        """
        Attempt to proceed to the next state by checking if all required fields have data.
        """
        state = StateAssistant.get_state(state_id)
        if not state:
            return StateAssistant.assistant_log(f"No state found with state_id '{state_id}'.")
        if all(v is not None and v != "" for v in state.required_fields.values()):
            state.status = "completed"
            StateAssistant._save_state_model(state)
            return StateAssistant.assistant_log(f"State '{state.state_name}' is complete. Proceeding to next state...")
        else:
            state.status = "in_progress"
            StateAssistant._save_state_model(state)
            return StateAssistant.assistant_log(StateAssistant.generate_prompt_for_missing(state_id))

if __name__ == "__main__":
    # Define a sample state with required fields
    state_id = "raiko4"
    state_name = "Deep Brain Stimulation Lead Placement"
    required_fields = {
        "side": "",
        "company": "",
        "target": "",
        "targeting": "",
        "nexframe": ""
    }
    obj = StateAssistant.StateObject(
        state_id=state_id,
        state_name=state_name,
        required_fields=required_fields,
        status="new"
    )

    StateAssistant.request("Where do we stand currently?", state_id=state_id)