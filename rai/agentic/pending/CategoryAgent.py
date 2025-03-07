import asyncio
from abc import ABC

from F import LIST

from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor


class RaiCategoryAgent(ABC, rAI, TextProcessor):
    @classmethod
    async def pipeline_async(cls, user_prompt:str):
        agent_instance = cls()
        return await agent_instance.run_async(user_prompt=user_prompt)

    async def run_async(self, user_prompt:str):
        try:
            industries:[str] = await rTextTools.tool_async(name="industry", user_prompt=user_prompt)
            category_results = rTextTools.tools(*LIST.flatten(industries), user_prompt=user_prompt)
            categories = []
            topic_agents = []
            topics = []
            for k,v in category_results.items():
                categories.extend(v)
                topic_agents.append(f"topic_{k}")
            if topic_agents:
                topic_results = rTextTools.tools(*topic_agents, user_prompt=user_prompt)
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
    # from rai.ingest.utilities.text_data import schedule_text
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
    # from rai.ingest.utilities.text_data import schedule_text as user_prompt
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