import json
from typing import List, Dict, Optional

from rai.agentic.ai_plugins.curator_plugin import CuratorPlugin
from rai.internal.redis_db import RedisDB

import json
from typing import List, Dict, Optional
import redis

redisdb = RedisDB()
redisdb.connect()

class AgentStateManager(CuratorPlugin, ):
    """
    A robust, stateless state manager for handling agent flows with Redis as the sole source of truth.
    All methods are static so that no class instance is required; every operation loads, modifies, and
    saves state directly to Redis.
    """

    @staticmethod
    def get_redis_client() -> redis.Redis:
        """
        Returns a Redis client instance.
        Adjust the connection parameters as needed for your environment.
        """
        return redisdb.redis_client

    @staticmethod
    def create_new_state(state_name: str, required_fields: List[str], state_id: Optional[str] = None) -> str:
        """
        Initialize a new state and store it in Redis.

        :param state_name: Name of the state.
        :param required_fields: List of required fields for this state.
        :param state_id: Optional unique identifier; if not provided, a slugified state name is used.
        :return: A success message including the state_id.
        """
        redis_client = AgentStateManager.get_redis_client()
        state_id = state_id if state_id else state_name.replace(" ", "_").lower()
        state_dict = {
            "state_name": state_name,
            "required_fields": required_fields,
            "data": {},
            "status": "created"
        }
        key = f"agent_state:{state_id}"
        redis_client.set(key, json.dumps(state_dict))
        return f"New state created with state_id '{state_id}'."

    @staticmethod
    def load_state(state_id: str) -> Dict:
        """
        Load the state from Redis.
        """
        redis_client = AgentStateManager.get_redis_client()
        key = f"agent_state:{state_id}"
        state_str = redis_client.get(key)
        if state_str:
            return json.loads(state_str)
        return {}

    @staticmethod
    def save_state(state_id: str, state: Dict) -> str:
        """
        Persist the state to Redis.
        """
        redis_client = AgentStateManager.get_redis_client()
        key = f"agent_state:{state_id}"
        redis_client.set(key, json.dumps(state))
        return f"State has been saved. [ Redis key '{key}' ]"

    @staticmethod
    def is_complete(state_id: str) -> bool:
        """
        Check if all required fields for the given state have been provided.
        """
        state = AgentStateManager.load_state(state_id)
        data = state.get("data", {})
        required_fields = state.get("required_fields", [])
        return all(field in data and data[field] is not None for field in required_fields)

    @staticmethod
    def missing_fields(state_id: str) -> List[str]:
        """
        Retrieve a list of required fields that are missing data for the given state.
        """
        state = AgentStateManager.load_state(state_id)
        data = state.get("data", {})
        required_fields = state.get("required_fields", "[]")
        parsed_fields = json.loads(required_fields.replace("\'", "\""))
        result = [field for field in parsed_fields if field not in data or data[field] is None]
        return result

    @staticmethod
    def attach_data(state_id: str, field: str, value: str) -> str:
        """
        Attach data to a specific field for the given state.
        """
        state = AgentStateManager.load_state(state_id)
        if not state:
            return f"No state found with state_id '{state_id}'."
        if field not in state.get("required_fields", []):
            return f"Field '{field}' is not a valid required field for state '{state.get('state_name')}'."

        # Update data for the field.
        data = state.get("data", {})
        data[field] = value
        state["data"] = data

        # Update status based on completeness.
        if all(f in data and data[f] is not None for f in state.get("required_fields", [])):
            state["status"] = "completed"
        else:
            state["status"] = "in_progress"

        AgentStateManager.save_state(state_id, state)
        return f"Data for field '{field}' attached."

    @staticmethod
    def generate_prompt_for_missing(state_id: str) -> str:
        """
        Generate a prompt listing the missing required data for the given state.
        """
        state = AgentStateManager.load_state(state_id)
        if not state:
            return "No state found!"
        missing = AgentStateManager.missing_fields(state_id)
        state_name = state.get("state_name", "")
        if missing:
            return f"Please provide the following data for state '{state_name}': {str(missing)}."
        else:
            return f"All required data has been provided for state '{state_name}'."

    @staticmethod
    def attempt_to_proceed_forward(state_id: str) -> str:
        """
        Attempt to proceed to the next state by checking for completeness.
        Updates the status accordingly.
        """
        state = AgentStateManager.load_state(state_id)
        if not state:
            return f"No state found with state_id '{state_id}'."

        if all(field in state.get("data", {}) and state["data"][field] is not None
               for field in state.get("required_fields", [])):
            state["status"] = "completed"
            AgentStateManager.save_state(state_id, state)
            return f"State '{state.get('state_name')}' is complete. Proceeding to next state..."
        else:
            # Update status to in_progress if any data exists.
            if any(field in state.get("data", {}) for field in state.get("required_fields", [])):
                state["status"] = "in_progress"
                AgentStateManager.save_state(state_id, state)
            return AgentStateManager.generate_prompt_for_missing(state_id)


if __name__ == "__main__":
    # Define a sample state with required fields
    state_name = "Deep Brain Stimulation Lead Placement"
    required_fields = [
        "Confirm Side",
        "Confirm company",
        "Confirm target",
        "Confirm targeting system",
        "Confirm nexframe array"
    ]

    # Initialize the state manager
    # state_manager = AgentStateManager()
    result = AgentStateManager.ask("I am confirming the side to be the right side of the head.", state_id="dpslp1")
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