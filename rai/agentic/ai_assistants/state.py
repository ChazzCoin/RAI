
from rai.agentic.ai_plugins.reason import rAssistantReasoningPlugin
import json
from typing import Any, Dict, Optional, Type, Union, List
from pydantic import BaseModel, Field

from rai.agentic.ai_tools.text_tools.r_tools import rTextTools


class rStateAssistant(rAssistantReasoningPlugin):
    """
    A robust, stateless state manager for handling agent flows with Redis as the sole source of truth.
    All methods are static so that no class instance is required; every operation loads, modifies, and
    saves state directly to Redis.
    """

    @staticmethod
    def _required_data_model_type() -> Type[BaseModel]:
        return rStateAssistant.StateObject

    @staticmethod
    def module_name() -> str: return "StateAssistant"

    class StateObject(BaseModel):
        state_id: str
        state_name: str
        required_fields: Dict[str, str] = Field(default_factory=dict)
        status: str = "started"

    @staticmethod
    def _required_model() -> Type[BaseModel]:
        return rStateAssistant.StateObject

    @staticmethod
    def assistant_rules() -> str:
        return """
        You will already have state_id.
        get_state: get latest external data
        create_new_state: create a new state
        DEFAULT STATE should be: 'started'
        IF required_fields data is missing: generate_prompt_for_missing
        IF all required_fields have data: attempt_to_proceed_forward
        """

    @classmethod
    def request(cls, user_prompt: str, **attached_data):
        """THIS IS NOT An AI FUNCTION CALL. DO NOT CALL THIS FUNCTION."""
        return cls().reason(user_request=user_prompt, **attached_data)

    @staticmethod
    def _get_redis_key(state_id: str) -> str:
        return f"agent_state:{state_id}"

    def extract_external_object(self, text: str) -> Union[str, Any]:
        """Extract external data object using AI."""
        # Use AI to extract required state data.
        external_object = rTextTools.formatter(
            text=text,
            model=self._required_data_model_type()
        )
        if not external_object:
            return self.assistant_error_log(
                f"Failed to extract the required data for the provided response format. [ {external_object} ]"
            )
        return external_object

    def magic_update(self, text: str):
        """Extract data using AI and update the state if it exists, or create a new state if not."""
        # Use AI to extract required state data.
        external_object = rTextTools.formatter(
            text=text,
            model=self._required_data_model_type()
        )
        if not external_object:
            return self.assistant_error_log(
                f"Failed to extract the required data for the provided response format. [ {external_object} ]"
            )

        # Determine the state_id using provided data or fall back to a slugified state_name.
        state_id = external_object.get("state_id")
        if not state_id:
            state_name = external_object.get("state_name", "default_state")
            state_id = state_name.replace(" ", "_").lower()
        else:
            state_name = external_object.get("state_name", state_id)

        key = self._get_redis_key(state_id)
        state_str = self.rRedis().get(key)

        if state_str:
            # If state exists, attempt to update it.
            try:
                state_data = json.loads(state_str)
                # Merge the new external data with the existing state.
                state_data.update(external_object)
                self.data = state_data
                self.rRedis().set(key, json.dumps(state_data))
                return self.assistant_log(
                    f"State with state_id '{state_id}' updated: {state_data}"
                )
            except Exception as e:
                return self.assistant_error_log(
                    f"Error updating state for key '{key}': {e}"
                )
        else:
            # No existing state: create a new state.
            required_fields = external_object.get("required_fields", external_object)
            new_state = {
                "state_id": state_id,
                "state_name": state_name,
                "required_fields": required_fields,
                "status": "started"
            }
            self.data = new_state
            self.rRedis().set(key, json.dumps(new_state))
            return self.assistant_log(
                f"New state created with state_id '{state_id}': {new_state}"
            )

    def create_new_state(self, state_id: Optional[str], state_name: str, required_fields: Union[str, Dict[str, str]]) -> str:
        """
        Initialize a new state and store it in Redis.
        :param state_id: Optional unique identifier; if not provided, a slugified state name is used.
        :param state_name: Name of the state.
        :param required_fields: Either a dict mapping field names to initial data or a JSON string representing that dict.
        :return: A success message including the state_id.
        """
        state_id = state_id or state_name.replace(" ", "_").lower()
        if self.get_state(state_id):
            return self.assistant_log(f"State with state_id '{state_id}' already exists.")

        # If required_fields is a string, attempt to parse it as JSON.
        if isinstance(required_fields, str):
            try:
                required_fields = json.loads(required_fields)
            except Exception as e:
                return self.assistant_log(f"Invalid required_fields JSON string: {e}")

        new_state = self.StateObject(
            state_id=state_id,
            state_name=state_name,
            required_fields=required_fields,
            status="started"
        )
        key = self._get_redis_key(state_id)
        self.rRedis().set(key, json.dumps(new_state.dict()))
        return self.assistant_log(
            f"create_new_state: New state created with state_id '{state_id}': {new_state.dict()}"
        )

    def get_state(self, state_id: str) -> Optional["StateObject"]:
        """Retrieve and parse the state from Redis into a StateObject."""
        key = self._get_redis_key(state_id)
        state_str = self.rRedis().get(key)
        self.assistant_log(f"Retrieving state for key: '{key}', data: {state_str}")
        if not state_str:
            self.assistant_log(f"No state found for key: '{key}'")
            self.data = None
            return None
        try:
            state_data = json.loads(state_str)
            self.data = state_data
            return self.StateObject.model_validate(state_data)
        except Exception as e:
            self.assistant_error_log(f"Error parsing state data for key '{key}': {e}")
            self.data = None
            return None

    def reset_state(self, state_id: str) -> str:
        """
        Reset the state for the given state_id to its initial configuration of no data.
        The dictionary of required_fields remains intact, but all values are set to empty strings.
        The state status is reset to "started".
        """
        state = self.get_state(state_id)
        if not state:
            return self.assistant_log(f"No state found with state_id '{state_id}' to reset.")

        # Reset all values in required_fields to an empty string.
        reset_fields = {key: "" for key in state.required_fields.keys()}
        state.required_fields = reset_fields
        state.status = "started"

        self._save_state_model(state)
        return self.assistant_log(
            f"State '{state.state_name}' with state_id '{state_id}' has been reset to its starting position."
        )
    def extract_state_id(self, text:str):
        # Use AI to extract required state data.
        class StateId(BaseModel):
            state_id: str

        stateId_object = self.llm().generate_format(
            user=text,
            system="Extract the state_id from the provided response format.",
            format=StateId
        )
        if not stateId_object:
            return self.assistant_error_log(
                f"Failed to extract the required data for the provided response format. [ {stateId_object} ]"
            )
        return stateId_object.state_id
    def magic_delete(self, text: str):
        """Extract state_id using AI and delete the state if it exists, or create a new state if not."""

        # Use AI to extract required state data.
        class StateId(BaseModel):
            state_id: str

        stateId_object = rTextTools.formatter(text=text, model=StateId)
        if not stateId_object:
            return self.assistant_error_log(
                f"Failed to extract the required data for the provided response format. [ {stateId_object} ]"
            )
        return self.delete_state(stateId_object.state_id)

    def delete_state(self, state_id: str) -> str:
        """Delete the state from Redis."""
        key = self._get_redis_key(state_id)
        try:
            response = self.rRedis().delete(key)
            return self.assistant_log(f"Deleted state with key '{key}'. Redis response: {response}")
        except Exception as e:
            return self.assistant_log(f"Error deleting state with key '{key}': {e}")

    def _save_state_model(self, state_model: "StateObject") -> str:
        """Persist the StateObject model to Redis."""
        key = self._get_redis_key(state_model.state_id)
        self.rRedis().set(key, json.dumps(state_model.dict()))
        return self.assistant_log(f"State saved for key '{key}'.")

    def save_state(self, state: Union["StateObject", dict]) -> str:
        """Save the state to Redis. Accepts either a StateObject instance or a dictionary."""
        if isinstance(state, dict):
            try:
                state = self.StateObject.parse_obj(state)
            except Exception as e:
                return self.assistant_log(f"Error converting dict to StateObject: {e}")
        self._save_state_model(state)
        return self.assistant_log(f"State with state_id '{state.state_id}' saved.")

    def is_complete(self, state_id: str) -> bool:
        """Check if all required fields have been provided with non-empty values."""
        state = self.get_state(state_id)
        if not state:
            return False
        return all(value is not None and value != "" for value in state.required_fields.values())

    def missing_fields(self, state_id: str) -> List[str]:
        """Retrieve a list of required fields that have missing or empty data."""
        state = self.get_state(state_id)
        if not state:
            self.assistant_log(f"No state found for state_id '{state_id}' to check missing fields.")
            return []
        missing = [field for field, value in state.required_fields.items() if not value]
        self.assistant_log(f"Missing fields for state '{state.state_name}': {missing}")
        return missing

    def attach_data(self, state_id: str, field: str, value: str) -> str:
        """Attach data to a specific field in required_fields and update the state status accordingly."""
        state = self.get_state(state_id)
        if not state:
            return self.assistant_log(f"No state found with state_id '{state_id}'.")
        if field not in state.required_fields:
            self.assistant_log(f"1. Field '{field}' is not valid for state '{state.state_name}'. Modifying to replace spaced with underscore.")
            field = field.replace(" ", "_")
            if field not in state.required_fields:
                self.assistant_log(f"2. Field '{field}' is not valid for state '{state.state_name}'. Modifying to replace underscore with spaced.")
                field = field.replace("_", " ")
                if field not in state.required_fields:
                    return self.assistant_log(f"3. Field '{field}' is not valid for state '{state.state_name}'. Neither modifications worked.")
        state.required_fields[field] = value

        # Update state status based on completeness.
        if all(v is not None and v != "" for v in state.required_fields.values()):
            state.status = "completed"
        else:
            state.status = "in_progress"
        self._save_state_model(state)
        return self.assistant_log(f"Data for field '{field}' attached in state '{state.state_name}'.")

    def update_required_fields(self, state_id: str, new_required_fields: Union[str, Dict[str, str]]) -> str:
        """Update the required_fields dictionary for the state and recalculate completeness."""
        state = self.get_state(state_id)
        if not state:
            return self.assistant_log(f"No state found with state_id '{state_id}'.")

        # If new_required_fields is a string, parse it as JSON.
        if isinstance(new_required_fields, str):
            try:
                new_required_fields = json.loads(new_required_fields)
            except Exception as e:
                return self.assistant_log(f"Invalid new_required_fields JSON string: {e}")

        state.required_fields = new_required_fields
        if all(v is not None and v != "" for v in new_required_fields.values()):
            state.status = "completed"
        else:
            state.status = "in_progress"
        self._save_state_model(state)
        return self.assistant_log(
            f"update_required_fields: Required fields updated to {new_required_fields} for state '{state.state_name}'."
        )

    def generate_prompt_for_missing(self, state_id: str) -> str:
        """Generate a prompt listing the missing required data for the state."""
        state = self.get_state(state_id)
        if not state:
            return "No state found!"
        missing = self.missing_fields(state_id)
        if missing:
            return self.assistant_log(
                f"Please provide the following data for state '{state.state_name}': {missing}."
            )
        else:
            return self.assistant_log(
                f"All required data has been provided for state '{state.state_name}'."
            )

    def attempt_to_proceed_forward(self, state_id: str) -> str:
        """Attempt to proceed to the next state by checking if all required fields have data."""
        state = self.get_state(state_id)
        if not state:
            return self.assistant_log(f"No state found with state_id '{state_id}'.")
        if all(v is not None and v != "" for v in state.required_fields.values()):
            state.status = "completed"
            self._save_state_model(state)
            return self.assistant_log(f"State '{state.state_name}' is complete. Proceeding to next state...")
        else:
            state.status = "in_progress"
            self._save_state_model(state)
            return self.assistant_log(self.generate_prompt_for_missing(state_id))

if __name__ == "__main__":
    # Define a sample state with required fields
    """
    Deep Brain Stimulation Lead Placement
    • Confirm Side
    • Confirm company
    • Confirm target
    • Confirm targeting system
    • Confirm nexframe array
    """
    state_id = "nora2"
    state_name = "Deep Brain Stimulation Lead Placement"
    required_fields = {
        "side": "",
        "company": "",
        "target": "",
        "targeting system": "",
        "nexframe array": "",
    }
    obj = rStateAssistant.StateObject(
        state_id=state_id,
        state_name=state_name,
        required_fields=required_fields,
        status="new"
    )

    rStateAssistant.request("What is the side set to currently?", state_id=state_id)