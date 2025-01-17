import asyncio
from abc import abstractmethod, ABC
from typing import List, Any

from rai.Async import AsyncTaskManager
from rai.base.BaseAgents import RaiBaseAgent, register_agent, AGENT_REGISTRY
from rai.data.utilities.TextUtils import TextProcessor

class RaiCompositeAgent(ABC, TextProcessor):
    fsync = AsyncTaskManager()
    @classmethod
    def pipeline(cls, name: str, user_prompt: str, sub: bool = False) -> Any:
        agent_classes = AGENT_REGISTRY.get(name)
        if not agent_classes:
            raise ValueError(f"No agent found with name '{name}'")
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return agent_instance.run(user_prompt=user_prompt, sub=sub)

    @classmethod
    async def pipeline_async(cls, name: str, user_prompt: str, sub: bool = False) -> Any:
        agent_classes = AGENT_REGISTRY.get(name)
        if not agent_classes:
            raise ValueError(f"No agent found with name '{name}'")
        cls.name = name
        agent_cls = agent_classes[0]
        agent_instance = agent_cls()
        return await agent_instance.run_async(user_prompt=user_prompt, sub=sub)

    @abstractmethod
    def type(self): pass
    @abstractmethod
    def base_agents(self) -> List[str]: pass

    def run(self, user_prompt: str, sub: bool = False) -> Any:
        try:
            results = []
            for agent in self.base_agents():
                results.append(RaiBaseAgent.pipeline(name=agent, user_prompt=user_prompt, sub=sub))
            return results
        except Exception as e:
            print(f"Error in RaiCompositeAgent.run: {e}")
            return None

    async def run_async(self, user_prompt: str, sub: bool = False) -> Any:
        try:
            tasks = []
            for agent in self.base_agents():
                task = asyncio.create_task(
                    RaiBaseAgent.pipeline_async(name=agent, user_prompt=user_prompt, sub=sub)
                )
                tasks.append(task)
            results = []
            for completed_task in asyncio.as_completed(tasks):
                try:
                    result = await completed_task
                    results.append(result)
                except Exception as exc:
                    print(exc)
                    continue
            return results
        except Exception as e:
            print(f"Error in RaiCompositeAgent.run: {e}")
            return None

@register_agent("extract_objects")
class AgentConfigPrimaryObjective(RaiCompositeAgent):
    def type(self): return ""
    def base_agents(self) -> List[str]:
        return [ "events", "contacts", "locations" ]

async def main():
    results = await RaiCompositeAgent.pipeline_async(
        name="extract_objects",
        user_prompt=schedule_text
    )
    if type(results) in [list, tuple]:
        for item in results:
            print(item)
    elif type(results) in [dict]:
        for item in results.items():
            print(item)
    else:
        print(results)
if __name__ == "__main__":
    from rai.data.utilities.text_data import schedule_text
    asyncio.run(
        main()
    )
    # results = RaiCompositeAgent.pipeline(
    #     name="object_extractor",
    #     user_prompt=schedule_text
    # )
    # print(results)
    #


