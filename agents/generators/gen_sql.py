from assistant import openai_client
from agents.prompts.text_to_sql import TEXT_TO_SQL_USER_PROMPT, TEXT_TO_SQL_SYSTEM_PROMPT
from config.postgres import PostgresSchemaExtractor
"""

"""

def convert_text_to_sql(user_details: str, database_schema: str):
    system_prompt = TEXT_TO_SQL_SYSTEM_PROMPT
    user_prompt = TEXT_TO_SQL_USER_PROMPT(user_details, database_schema)
    sql_query = openai_client.chat_request(system_prompt, user_prompt)
    print(sql_query)
    return sql_query

details = "I want to send my team an email about all sales and revenue data."
db = PostgresSchemaExtractor()
schema = db.fetch_schema()
convert_text_to_sql(details, schema)