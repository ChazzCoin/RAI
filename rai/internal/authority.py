import os

from dotenv import load_dotenv, dotenv_values
from typing import Optional, Dict, List

from datetime import datetime
from typing import Optional

from rai.internal import fBaseModel
from rai.internal.clients.redis_client import RedisDB

redis_client = RedisDB().connect()

class fVault(fBaseModel):
    name: Optional[str] = None
    client_name: Optional[str] = None
    service_name: str = "env"
    date_created: datetime = datetime.utcnow().timestamp()
    prefix: Optional[str] = None
    is_enabled: bool = False
    description: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    additional_info: Optional[dict] = None
    sesson_id: Optional[str] = None
    env_name: Optional[str] = None
    env_value: Optional[str] = None

    def from_env(self, key:str=None) -> 'fVault':
        value = redis_client.get(f"env:{key or self.env_name}")
        obj = value.decode()
        if key: self.env_name = key
        self.env_value = obj
        return self

    def to_env(self):
        return redis_client.set(f"env:{self.env_name}", self.env_value)

    def to_vault(self):
        return redis_client.set(f"vault:{self.name}", self.model_dump())

    @classmethod
    def from_vault(cls, name: str):
        data = redis_client.get(f"vault:{name}")
        if data:
            return cls.model_validate(data)
        return None

class CentralAuthority:

    redis_client = None
    dotenv_path = './../../.env'

    vault = []
    env_vault = []
    cred_vault = []

    def __init__(self):
        self.init()

    def init(self):
        self.redis_client = redis_client.redis_client
        load_dotenv(self.dotenv_path)
        self.build_env_vault_list()
        # self.import_env_to_redis()

    # Breaker management
    def set_breaker(self, name: str, is_enabled: bool, description: Optional[str] = None):
        breaker = {'is_enabled': is_enabled, 'description': description}
        return self.redis_client.hset(f"breaker:{name}", mapping=breaker)

    def get_breaker(self, name: str) -> Optional[Dict[str, str]]:
        breaker_data = self.redis_client.hgetall(f"breaker:{name}")
        if breaker_data:
            return {k.decode(): v.decode() for k, v in breaker_data.items()}
        return None

    def switch_on(self, name: str):
        return self.redis_client.hset(f"breaker:{name}", "is_enabled", "True")

    def switch_off(self, name: str):
        return self.redis_client.hset(f"breaker:{name}", "is_enabled", "False")

    def switch(self, name: str):
        breaker = self.get_breaker(name)
        if breaker:
            new_state = "False" if breaker.get("is_enabled") == "True" else "True"
            return self.redis_client.hset(f"breaker:{name}", "is_enabled", new_state)

    def delete_breaker(self, name: str):
        return self.redis_client.delete(f"breaker:{name}")

    def list_breakers(self) -> List[str]:
        keys = self.redis_client.keys('breaker:*')
        return [key.decode().split(":")[1] for key in keys]

    # .env management
    def import_env_to_redis(self):
        env_vars = dotenv_values(self.dotenv_path)
        for key, value in env_vars.items():
            self.redis_client.set(f"env:{str(key)}", str(value))

    def build_env_vault_list(self) -> List[fVault]:
        vars = self.list_env_vars()
        for k,v in vars.items():
            obj = fVault(
                id=k,
                service_name="env",
                env_name=k,
                env_value=v
            )
            self.env_vault.append(obj)
            self.vault.append(obj)
        return self.env_vault

    def get_env(self, key: str, default=None) -> Optional[str]:
        try:
            value = self.redis_client.get(f"env:{key}")
            if value: return value.decode()
        except Exception as e:
            print(e)
        default = os.environ.get(key, default)
        self.set_env(key, default)
        return default

    def set_env(self, key: str, value: str):
        return self.redis_client.set(f"env:{key}", value)

    def update_env(self, key: str, value: str):
        if self.redis_client.exists(f"env:{key}"):
            return self.redis_client.set(f"env:{key}", value)

    def delete_env(self, key: str):
        return self.redis_client.delete(f"env:{key}")

    def list_env_vars(self) -> Dict[str, str]:
        keys = self.redis_client.keys('env:*')
        return {key.decode().split(":")[1]: self.redis_client.get(key).decode() for key in keys}

    """ Credentials Vault """

    def store_credentials(self, key: str, credentials: fVault):
        serialized_credentials = credentials.model_dump()
        self.redis_client.set(key, serialized_credentials)

    def retrieve_credentials(self, key: str) -> Optional[fVault]:
        serialized_credentials = self.redis_client.get(key)
        if serialized_credentials:
            return fVault.model_validate(serialized_credentials)
        return None

    def delete_credentials(self, key: str):
        return self.redis_client.delete(key)

    def list_all_credentials(self) -> List[str]:
        return [key.decode('utf-8') for key in self.redis_client.keys('vault:*')]


AUTHORITY = CentralAuthority()

# Example usage:
if __name__ == '__main__':
    authority = CentralAuthority()
    print(authority.vault)
    # Breaker usage
    # authority.set_breaker('maintenance_mode', False, 'Maintenance mode switch')
    # authority.switch('maintenance_mode')
    # breaker = authority.get_breaker('maintenance_mode')
    # print(f"Breaker state: {'enabled' if breaker['is_enabled'] == 'True' else 'disabled'}")
    #
    # # .env management
    # authority.import_env_to_redis()
    # db_host = authority.get_env('DATABASE_HOST')
    # print(f"Database host: {db_host}")
