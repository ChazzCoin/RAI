
from typing import List, Dict, Any, Type

from pydantic import BaseModel

from rai.agentic.agent_modules.engine import ToolEngine, register_tool_engine
from rai.agentic.agent_modules.result import ToolResult


@register_tool_engine('ollama')
class OllamaTool(ToolEngine):

    @staticmethod
    def tool_assistant_name() -> str: return "Ollama"
    @staticmethod
    def assistant_rules() -> str:
        return f"""
            You understand users natural language and convert it into a function.
            You manage an Ollama API Instance that runs LLM models.
        """
    def _required_data_model_type(self) -> Type[BaseModel]:
        """Return the required data model for the assistant."""
        return Type[BaseModel]

    def get_tools(self) -> List[dict[str, Any]]:
        return [
            self.get_tool('get_ollama_models'),
            self.get_tool('get_running_ollama_models'),
            self.get_tool('download_ollama_model'),
            self.get_tool('delete_ollama_model'),
            self.get_tool('finish')
        ]
    async def get_current_state(self) -> ToolResult:
        return self._tool_result
    def finish(self, **kwargs):
        return self.finish_and_then_respond()

    """ Custom Functions """
    def get_ollama_models(self, **kwargs) -> ToolResult:
        models = self.think.OLLAMA.list_models()
        return ToolResult(
            output="I have grabbed the available ollama llm models.",
            result=str(models),
            success=True
        )
    def get_running_ollama_models(self, **kwargs):
        models = self.think.OLLAMA.ps()
        return ToolResult(
            output="I have grabbed the currently running ollama llm models.",
            result=str(models),
            success=True
        )
    async def delete_ollama_model(self, model:str):
        response = await self.think.OLLAMA.delete_ollama_model(model)
        return ToolResult(
            output=f"I have deleted the ollama llm model [ {model} ]",
            result=str(response),
            success=True
        )
    def download_ollama_model(self, model:str):
        results = []
        for item in self.think.OLLAMA.download_ollama_model(model):
            results.append(item)
        return ToolResult(
            output=f"I have downloaded the ollama llm model [ {model} ]",
            result='\n'.join(results),
            success=True
        )

if __name__ == "__main__":
    request = "What models are available?"
    OllamaTool.runner(OllamaTool.go(request=request))
