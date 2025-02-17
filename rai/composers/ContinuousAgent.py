import asyncio
from abc import ABC

from rai.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent
from rai.assistant.connectors import RaiAi
from rai.data.utilities.TextUtils import TextProcessor



class RaiContinuousAgent(ABC, RaiAi, TextProcessor):
    run_count = 0
    responses = []

    @classmethod
    async def pipeline_async(cls, name:str, user_prompt:str, runs:int):
        agent_instance = cls()
        return await agent_instance.run_async(name=name, user_prompt=user_prompt, runs=runs)

    async def run_async(self, name:str, user_prompt:str, runs:int) -> [str]:
        try:
            u_prompt = user_prompt
            r_prompt = ""
            while self.run_count <= runs:
                f_prompt = user_prompt
                if self.run_count >= 1:
                    f_prompt = f"ORIGINAL PROMPT:\n {u_prompt} \nI want you to continue generating the following...\n{str(r_prompt)}"
                r_prompt = await RaiBaseTextAgent.generate_async(name=name, user_prompt=f_prompt)
                print(r_prompt)
                self.responses.append(r_prompt)
                self.run_count = self.run_count + 1
            return r_prompt
        except Exception as e:
            print(f"Error: {e}")
            return None



async def main(user_prompt):
    # from rai.data.utilities.text_data import schedule_text
    results = await RaiContinuousAgent.pipeline_async(
            name="step_by_step",
            user_prompt=user_prompt,
            runs=10
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
    user_prompt = "How do you build an engine?"
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