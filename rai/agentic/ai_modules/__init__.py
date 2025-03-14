from typing import List

ASSISTANT_LOG_CHAIN = []

class mAssistLog:

    @classmethod
    def assistant_log(cls, *data: str) -> str:
        """Log messages to the assistant log chain."""
        for line in data:
            info_message = f"r{cls.__name__}: INFO: " + line
            print(info_message)
            ASSISTANT_LOG_CHAIN.append(info_message)
        return str(data)

    @classmethod
    def assistant_error_log(cls, *data: str) -> str:
        """Log error messages with an 'ERROR:' prefix."""
        for line in data:
            error_message = f"r{cls.__name__}: ERROR: " + line
            print(error_message)
            ASSISTANT_LOG_CHAIN.append(error_message)
        return str(data)

    @staticmethod
    def get_assistant_log() -> List[str]:
        """Retrieve the assistant log as a list of strings."""
        return ASSISTANT_LOG_CHAIN

    @staticmethod
    def get_assistant_log_str() -> str:
        """Retrieve the assistant log as a single string."""
        return str(ASSISTANT_LOG_CHAIN)



