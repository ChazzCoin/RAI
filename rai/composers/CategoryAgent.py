import asyncio
from abc import ABC

from F import LIST

from rai.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.assistant.connectors import RaiAi
from rai.data.utilities.TextUtils import TextProcessor



class RaiCategoryAgent(ABC, RaiAi, TextProcessor):
    @classmethod
    async def pipeline_async(cls, user_prompt:str):
        agent_instance = cls()
        return await agent_instance.run_async(user_prompt=user_prompt)

    async def run_async(self, user_prompt:str):
        try:
            industries:[str] = await RaiBaseTextAgent.generate_async(name="industry", user_prompt=user_prompt)
            category_results = RaiBaseTextAgent.generates(*LIST.flatten(industries), user_prompt=user_prompt)
            categories = []
            topic_agents = []
            topics = []
            for k,v in category_results.items():
                categories.extend(v)
                topic_agents.append(f"topic_{k}")
            if topic_agents:
                topic_results = RaiBaseTextAgent.generates(*topic_agents, user_prompt=user_prompt)
                if topic_agents:
                    for k, v in topic_results.items():
                        topics.extend(v)
            return {
                "industries": industries,
                "categories": LIST.flatten(categories),
                "topics": LIST.flatten(topics),
            }
        except Exception as e:
            print(f"Error: {e}")
            return None



async def main(user_prompt):
    # from rai.data.utilities.text_data import schedule_text
    results = await RaiCategoryAgent.pipeline_async(
            user_prompt=user_prompt
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
    # from rai.data.utilities.text_data import schedule_text as user_prompt
    user_prompt = "How do i register for tryouts with the soccer club?"
    asyncio.run(
        main(
            user_prompt=user_prompt
        )
    )
    # asyncio.run(
    #     main(
    #         name="subject",
    #         user_prompt=user_prompt
    #     )
    # )