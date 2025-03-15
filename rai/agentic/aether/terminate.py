from rai.agentic.aether.tool import BaseTool


_TERMINATE_DESCRIPTION = """Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
When you have finished all the tasks, call this tool to end the work."""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    def ask_ai_to_generate_final_response(self, prompt) -> str:
        """AI CALL: Attempt to establish an objective based on the provided prompt."""
        try:
            from rai.assistant.connectors import LLM
            print("Generating final response for user.")

            response = LLM.generate(
                user=prompt,
                system="Based on the data provided, create the appropriate response to send back to the user."
            )
            print("Final Response Generated", response)
            return f"<FINAL RESPONSE>\n{response}\n</FINAL RESPONSE>"
        except Exception as e:
            return f"<FINAL RESPONSE>\n Failed to generate final response with error: [ {e} ]\n</FINAL RESPONSE>"

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        print(f"The interaction has been completed with status: {status}")
        return self.ask_ai_to_generate_final_response(status)

