import asyncio
from abc import ABC
from rai.raigents.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.assistant.connectors import RaiAi
from rai.raigents.base.BaseContexts import RaiBaseContexts
from rai.ingest.utilities.TextUtils import TextProcessor



class RaiContextAgent(ABC, RaiAi, TextProcessor):
    @classmethod
    async def pipeline_async(cls, user_prompt:str, context:str):
        agent_instance = cls()
        return await agent_instance.run_async(user_prompt=user_prompt, context=context)

    async def run_async(self, user_prompt:str, context:str) -> [str]:
        try:
            context_prompt = RaiBaseContexts.pipeline(context)
            expanded = await RaiBaseTextAgent.generate_async(name="context_expander", user_prompt=user_prompt, system_prompt=context_prompt)
            return expanded
        except Exception as e:
            print(f"Error: {e}")
            return None



async def main(user_prompt, context):
    # from rai.ingest.utilities.text_data import schedule_text
    results = await RaiContextAgent.pipeline_async(
            user_prompt=user_prompt,
            context=context
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
    user_prompt = "How do I register my 8 year old?"
    asyncio.run(
        main(
            user_prompt=user_prompt,
            context="soccer"
        )
    )
    # asyncio.run(
    #     main(
    #         name="subject",
    #         user_prompt=user_prompt
    #     )
    # )