from rai.assistant import openai_client
from rai.agents.prompts.team_email import TEAM_UPDATE_SYSTEM_PROMPT, USER_TEAM_EMAIL_PROMPT

"""
1. Grab System Prompt for Type of Email
2. Grab User Prompt for Email Content
3. Call OpenAI API to generate email
4. Validate email
5. Return email to user

X. Send Email to Team
"""

def generate_team_email(subject: str, body: str):
    system_prompt = TEAM_UPDATE_SYSTEM_PROMPT
    user_prompt = USER_TEAM_EMAIL_PROMPT(subject, body)
    email = openai_client.openai_generate(system_prompt, user_prompt)
    print(email)
    return email


# generate_team_email("Practice Schedule Update", "Hello Team,\n\nWe will be having practice tomorrow at 4:30 PM at the soccer field. Please make sure to bring your equipment and water bottles.\n\nThanks,\nCoach John")