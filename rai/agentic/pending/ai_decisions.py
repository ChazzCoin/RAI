from F import LIST

from rai.agentic.ai_tools.text_tools.text_functions import aiTextFunctions
from rai.assistant.connectors import rAI

DECISIONS = {
        "TokenSizeError": "Reduce or truncate the input token size (or summarize input) to meet constraints.",
        "TimeoutError": "Retry after a brief delay or adjust timeout settings.",
        "RateLimitError": "Wait for a defined period (e.g., 5-10 seconds) before retrying.",
        "AuthenticationError": "Revalidate credentials or refresh the authentication token.",
        "ServerError": "Retry using exponential backoff, as the error may be transient.",
        "UnknownError": "Log error details and escalate for further review."
    }


class rAiErrorHandler(rAI):
    def type(self):
        return "no_args"

    @staticmethod
    def getFunctionJsonNoArgs(name, description) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description
            },
        }

    def decide(self, error_message:str):
        try:
            options = self.engine.generate_function(
                user=error_message,
                system=self.system_prompt(),
                functions=self.build()
            )
            option = LIST.get(0, options, None)
            if option is None:
                return self.unknown_error()
            elif option == 'token_size_error':
                return self.token_size_error()
            elif option == 'timeout_error':
                return self.timeout_error()
            elif option == 'rate_limit_error':
                return self.rate_limit_error()
            elif option == 'authentication_error':
                return self.authentication_error()
            elif option == 'server_error':
                return self.server_error()
            return self.unknown_error()
        except Exception as e:
            return self.unknown_error()

    def build(self) -> [dict]:
        return [ self.getFunctionJsonNoArgs(key, value) for key, value in self.decisions().items() ]

    def system_prompt(self):
        return """
            You are an AI assistant tasked with determining how to handle the user prompts HTTP error. 
            Analyze the structure of the text and determine the type of error. 
            Read the functions below to determine the function or action to handle the error. 
        """

    def decisions(self) -> dict:
        return {
            "token_size_error": "Triggered when the input exceeds token size or limit constraints.",
            "timeout_error": "Triggered when the API call times out without a response.",
            "rate_limit_error": "Triggered when the request frequency exceeds allowed limits.",
            "authentication_error": "Triggered when there is an issue with credentials or access tokens.",
            "server_error": "Triggered when the server encounters an internal error while processing the request.",
            "unknown_error": "Triggered when the error doesn't match any known category and requires further investigation."
        }

    def token_size_error(self):
        pass
    def timeout_error(self):
        pass
    def rate_limit_error(self):
        pass
    def authentication_error(self):
        pass
    def server_error(self):
        pass
    def unknown_error(self):
        pass
