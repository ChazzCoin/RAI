from rai.assistant import openai_client
from rai.agents.prompts.scheduler import SCHEDULER_SPORTS_SYSTEM_PROMPT


"""

"""

def generate_schedule():
    system_prompt = SCHEDULER_SPORTS_SYSTEM_PROMPT
    user_prompt = """
    2 complexes: Complex A (10 fields) and Complex B (4 fields)
    56 Teams: Team A, Team B...Team AA, Team AB...
    Dates: August 1st - December 31st
    Time Slots: 4:30 PM Start - 10:00 PM End
    Blackout Dates: November 20th - November 27th, December 19th - December 27th
    """
    sql_query = openai_client.openai_generate(system_prompt, user_prompt)
    print(sql_query)
    return sql_query

generate_schedule()