from rai.assistant import openai_client

Auto_Format = """
You will decide based on the data how it should be split up and formatted for human readability.
"""

Chromadb_Format = """
You will clean and reformat this data so it can be properly embedded and inserted into ChromaDB Vector Database.
"""

System_Prompt = lambda format_type: f"""
You are now my personal AI Data Assistant.

1. I will provide you with raw datasets of text.
2. You will read through the data.

Format Response Type
{format_type}

Only return the formatted data.
"""

def request_auto_format_of_raw_data(raw_text: str):
    return openai_client.openai_generate(System_Prompt(Auto_Format), raw_text, model="gpt-4o-mini")

def request_chromadb_format(raw_text: str):
    return openai_client.openai_generate(System_Prompt(Chromadb_Format), raw_text, model="gpt-4o-mini")
