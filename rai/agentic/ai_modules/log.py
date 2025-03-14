
from rai.internal.clients.redis_client import RedisDB

redis = RedisDB()

class mLog:
    """
    A logging module that supports caching logs in Redis so that logs persist between runs.
    Logs are categorized into INFO/ERROR (stored together in "mLog:LOG"), WARNING ("mLog:WARNING"),
    and VERBOSE ("mLog:VERBOSE"). The Redis client is expected to be provided during initialization.
    """

    redis_client = redis.connect().redis_client

    key = "mlog"
    name = "system"

    LOG = []
    DATA = []
    WARNING = []
    VERBOSE = []

    def __init__(self, name:str="system"):
        self.name = name
        self.restore_logs_from_cache()

    def set_name(self, name:str): self.name = name
    def log_key(self): return f"{self.key}:{self.name}:LOG"
    def data_key(self): return f"{self.key}:{self.name}:DATA"
    def warning_key(self): return f"{self.key}:{self.name}:WARNING"
    def verbose_key(self): return f"{self.key}:{self.name}:VERBOSE"

    def restore_logs_from_cache(self):
        # Restore logs from Redis
        self.LOG = self._load_logs(self.log_key())
        self.DATA = self._load_logs(self.data_key())
        self.WARNING = self._load_logs(self.warning_key())
        self.VERBOSE = self._load_logs(self.verbose_key())

    def _load_logs(self, key: str) -> list:
        try:
            logs = self.redis_client.lrange(key, 0, -1)
            return [log.decode("utf-8") if isinstance(log, bytes) else log for log in logs]
        except Exception as e:
            self.log_error(f"Error loading logs for key {key}: {e}")
            return []

    def _push_log(self, key: str, message: str) -> None:
        try:
            self.redis_client.rpush(key, message)
        except Exception as e:
            self.log_error(f"Error pushing log to key {key}: {e}")

    def delete_logs(self) -> None:
        keys = [self.log_key(), self.warning_key(), self.verbose_key()]
        for key in keys:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                self.log_error(f"Error deleting logs for key {key}: {e}")
        # Clear local log storage
        self.LOG.clear()
        self.DATA.clear()
        self.WARNING.clear()
        self.VERBOSE.clear()
        self.log("All logs have been deleted from both Redis and local cache.")

    def log(self, msg: str, level:str="INFO"):
        if level == "INFO": return self.log_info(msg)
        elif level == "DATA": return self.log_data(msg)
        elif level == "WARNING": return self.log_warning(msg)
        elif level == "VERBOSE": return self.log_verbose(msg)

    def log_info(self, msg: str) -> str:
        formatted_msg = f"{self.name}: INFO: {msg}"
        print(formatted_msg)
        self.LOG.append(formatted_msg)
        self._push_log(self.log_key(), formatted_msg)
        return formatted_msg

    def log_data(self, msg: str) -> str:
        formatted_msg = f"{self.name}: DATA ASSISTANT: {msg}"
        print(formatted_msg)
        self.LOG.append(formatted_msg)
        self._push_log(self.data_key(), formatted_msg)
        return formatted_msg

    def log_warning(self, msg: str) -> str:
        formatted_msg = f"{self.name}: WARNING: {msg}"
        self.WARNING.append(formatted_msg)
        self._push_log(self.warning_key(), formatted_msg)
        return formatted_msg

    def log_error(self, msg: str) -> str:
        formatted_msg = f"{self.name}: ERROR: {msg}"
        print(formatted_msg)
        self.LOG.append(formatted_msg)
        self._push_log(self.log_key(), formatted_msg)
        return formatted_msg

    def log_verbose(self, msg: str) -> str:
        formatted_msg = f"{self.name}: VERBOSE: {msg}"
        self.VERBOSE.append(formatted_msg)
        self._push_log(self.verbose_key(), formatted_msg)
        return formatted_msg

    def get_log(self, level:str="INFO") -> []:
        if level == "INFO": return self.LOG
        elif level == "DATA": return self.DATA
        elif level == "WARNING": return self.WARNING
        elif level == "VERBOSE": return self.VERBOSE

    def get_log_str(self, level:str="INFO"):
        if level == "INFO": return "\n".join(self.LOG)
        elif level == "DATA": return "\n".join(self.DATA)
        elif level == "WARNING": return "\n".join(self.WARNING)
        elif level == "VERBOSE": return "\n".join(self.VERBOSE)

    def print_logs(self, level:str="INFO"):
        if level.capitalize() == "INFO":
            for log in self.LOG: print(log)
        elif level.capitalize() == "DATA":
            for log in self.DATA: print(log)
        elif level.capitalize() == "WARNING":
            for log in self.WARNING: print(log)
        elif level.capitalize() == "VERBOSE":
            for log in self.VERBOSE: print(log)

if __name__ == "__main__":
    logger = mLog()
    logger.set_name("test")
    logger.restore_logs_from_cache()
    # logger.log("this is a logging test")
    # logger.log("cowboys and aliens")
    logger.print_logs()