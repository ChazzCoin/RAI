from typing import Optional

from rai.internal.redis_db import RedisDB

import json
from datetime import datetime
import logging

class RedisSession(RedisDB):
    def __init__(self):
        super().__init__()
        self.connect()
        self.logger = logging.getLogger(self.__class__.__name__)
    def _session_key(self, id:str) -> str:
        """
        Build the Redis key for the session.
        """
        return f"session:{id}"
    def create_session(self, id:str, knowledge_prefix: str, **kwargs) -> Optional[dict]:
        """
        Create and store a new session in Redis.

        :param status: The initial status of the session.
        :return: The session data as a dictionary.
        :raises Exception: When unable to create the session in Redis.
        """
        now = datetime.utcnow().isoformat()
        session_data = {
            "id": id,
            "knowledge_prefix": knowledge_prefix,
            "status":"new",
            "date_created": now,
            "date_updated": now
        }
        try:
            kwargmini = kwargs['kwargs']
            kwargs = json.loads(kwargmini)
            session_data.update(**kwargs)
        except Exception as e:
            self.logger.exception("Failed to update session: %s", e)
        try:
            # Store the session data as a JSON string in Redis
            result = self.redis_client.set(self._session_key(id=id), json.dumps(session_data))
            if not result:
                self.logger.error("Failed to create session in Redis for key: %s", self._session_key(id=id))
            self.logger.info("Session created: %s", id)
            return session_data
        except Exception as e:
            self.logger.exception("Error creating session: %s", e)
    def get_session(self, id:str) -> Optional[dict]:
        """
        Retrieve the session from Redis.

        :return: The session data as a dictionary, or None if not found.
        :raises Exception: When there is an error during retrieval.
        """

        try:
            data = self.redis_client.get(self._session_key(id=id))
            if data:
                self.logger.info("Session retrieved: %s", id)
                return json.loads(data)
            else:
                self.logger.warning("Session not found: %s", id)
                return None
        except Exception as e:
            self.logger.exception("Error retrieving session: %s", e)
    def update_session(self, id:str, **kwargs) -> Optional[dict]:
        """
        Update the session with provided fields and refresh the 'date_updated' timestamp.

        :param kwargs: Arbitrary keyword arguments to update the session.
        :return: The updated session data as a dictionary.
        :raises Exception: When session update fails.
        """
        try:
            session_data = self.get_session(id)
            if not session_data:
                self.logger.warning("No session found to update for: %s", id)
                return None
            try:
                kwargmini = kwargs['kwargs']
                kwargs = json.loads(kwargmini)
            except Exception as e:
                self.logger.exception("Failed to update session: %s", e)
            # Update session data with provided values

            session_data.update(**kwargs)
            session_data["date_updated"] = datetime.utcnow().isoformat()

            result = self.redis_client.set(self._session_key(id=id), json.dumps(session_data))
            if not result:
                self.logger.error("Failed to update session in Redis for key: %s", self._session_key(id=id))
            self.logger.info("Session updated: %s", id)
            return session_data
        except Exception as e:
            self.logger.exception("Error updating session: %s", e)
    def delete_session(self, id:str) -> Optional[int]:
        """
        Delete the session from Redis.

        :return: The number of keys removed (0 if not found, 1 if deleted).
        :raises Exception: When deletion fails.
        """
        try:
            result = self.redis_client.delete(self._session_key(id=id))
            if result == 0:
                self.logger.warning("Session not found or already deleted: %s", id)
            else:
                self.logger.info("Session deleted: %s", id)
            return result
        except Exception as e:
            self.logger.exception("Error deleting session: %s", e)

# if __name__ == "__main__":
    # print(RedisSession.request("get session with id 'chazzromeo'"))