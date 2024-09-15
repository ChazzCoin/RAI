import os
from assistant import openai_client as api
from assistant.rag import RAGWithChroma

# model = os.getenv("DEFAULT_OPENAI_MODEL")
model = "gpt-4o-mini"
collection = "web_pages_2"

user_prompt = f"""
My child is a goalkeeper, what kind of programs and options does my child have? What specific goalkeeper stuff does the club offer?
"""

def run():
    """ 0. Setup Dependencies """
    rag = RAGWithChroma(collection_name=collection)

    """ 1. Form Prompts """
    results = rag.query(user_prompt)
    system_prompt = rag.inject_into_system_prompt(results)
    print(system_prompt, "\n------------\n")

    """ 2. Request AI Response """
    ai_response = api.chat_request(system=system_prompt, user=user_prompt, model=model)

    """ 3. Form Final Chat Response """
    output = rag.append_metadata_to_response(ai_response, results)

    """ 4. Print and Return Response """
    print("\nMODEL:\n", model)
    print("\nQUESTION:\n", user_prompt)
    print("\nANSWER:\n", output)
    return output

if __name__ == "__main__":
    run()