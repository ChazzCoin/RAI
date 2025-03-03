from rai.internal.redis_db import RedisClient


class RaiCache(RedisClient):

    def __init__(self, db:int=0):
        super().__init__(db=db)

    def cache_announcement(self, key_name, data, ttl=None):
        """Cache an announcement or message."""
        try:
            self.set_key(f"announcement:{key_name}", data, ttl)
            print(f"Announcement '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache announcement '{key_name}': {e}")
            raise

    def get_announcement(self, key_name):
        """Retrieve a cached announcement or message."""
        try:
            return self.get_key(f"announcement:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve announcement '{key_name}': {e}")
            raise

    def cache_weather_data(self, key_name, data, ttl=43200):
        """Cache weather data with a default TTL of 12 hours (43200 seconds)."""
        try:
            self.set_key(f"weather:{key_name}", data, ttl)
            print(f"Weather data '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache weather data '{key_name}': {e}")
            raise

    def get_weather_data(self, key_name):
        """Retrieve cached weather data."""
        try:
            return self.get_key(f"weather:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve weather data '{key_name}': {e}")
            raise

    def cache_chat_message(self, chat_id, message_id, data, ttl=None):
        """Cache a chat message."""
        try:
            key = f"chat:{chat_id}:{message_id}"
            self.set_key(key, data, ttl)
            print(f"Chat message '{key}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache chat message '{key}': {e}")
            raise

    def get_chat_message(self, chat_id, message_id):
        """Retrieve a cached chat message."""
        try:
            key = f"chat:{chat_id}:{message_id}"
            return self.get_key(key)
        except Exception as e:
            print(f"Failed to retrieve chat message '{key}': {e}")
            raise

    def cache_chromadb_query(self, key_name, data, ttl=None):
        """Cache a ChromaDB query and its results."""
        try:
            self.set_key(f"chromadb:{key_name}", data, ttl)
            print(f"ChromaDB query '{key_name}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache ChromaDB query '{key_name}': {e}")
            raise

    def get_chromadb_query(self, key_name):
        """Retrieve a cached ChromaDB query and its results."""
        try:
            return self.get_key(f"chromadb:{key_name}")
        except Exception as e:
            print(f"Failed to retrieve ChromaDB query '{key_name}': {e}")
            raise

    def cache_field_status(self, field_id, status, ttl=None):
        """Cache the status of a field (ON or OFF)."""
        try:
            self.set_key(f"field_status:{field_id}", status, ttl)
            print(f"Field status for '{field_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache field status '{field_id}': {e}")
            raise

    def get_field_status(self, field_id):
        """Retrieve the cached status of a field."""
        try:
            return self.get_key(f"field_status:{field_id}")
        except Exception as e:
            print(f"Failed to retrieve field status '{field_id}': {e}")
            raise

    def cache_game_schedule(self, game_id, data, ttl=None):
        """Cache a game schedule."""
        try:
            self.set_key(f"game_schedule:{game_id}", data, ttl)
            print(f"Game schedule '{game_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache game schedule '{game_id}': {e}")
            raise

    def get_game_schedule(self, game_id):
        """Retrieve a cached game schedule."""
        try:
            return self.get_key(f"game_schedule:{game_id}")
        except Exception as e:
            print(f"Failed to retrieve game schedule '{game_id}': {e}")
            raise

    def cache_team_standings(self, league_id, data, ttl=None):
        """Cache team standings for a league."""
        try:
            self.set_key(f"team_standings:{league_id}", data, ttl)
            print(f"Team standings for league '{league_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache team standings for league '{league_id}': {e}")
            raise

    def get_team_standings(self, league_id):
        """Retrieve cached team standings for a league."""
        try:
            return self.get_key(f"team_standings:{league_id}")
        except Exception as e:
            print(f"Failed to retrieve team standings for league '{league_id}': {e}")
            raise

    def cache_player_profile(self, player_id, data, ttl=None):
        """Cache a player's profile."""
        try:
            self.set_key(f"player_profile:{player_id}", data, ttl)
            print(f"Player profile '{player_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache player profile '{player_id}': {e}")
            raise

    def get_player_profile(self, player_id):
        """Retrieve a cached player's profile."""
        try:
            return self.get_key(f"player_profile:{player_id}")
        except Exception as e:
            print(f"Failed to retrieve player profile '{player_id}': {e}")
            raise

    def cache_practice_notification(self, team_id, data, ttl=None):
        """Cache a practice notification for a team."""
        try:
            self.set_key(f"practice_notification:{team_id}", data, ttl)
            print(f"Practice notification for team '{team_id}' cached successfully.")
        except Exception as e:
            print(f"Failed to cache practice notification for team '{team_id}': {e}")
            raise

    def get_practice_notification(self, team_id):
        """Retrieve a cached practice notification for a team."""
        try:
            return self.get_key(f"practice_notification:{team_id}")
        except Exception as e:
            print(f"Failed to retrieve practice notification for team '{team_id}': {e}")
            raise

