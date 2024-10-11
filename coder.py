from rai.assistant import openai_client as api
from chdb.rag import RAGWithChroma

user_prompt = f"""
Tell me about the futures program at park city soccer club...
"""

def run(input:str):
    rag = RAGWithChroma()
    # Form Prompts
    results = rag.query(input)
    print(results, "\n------------\n")
    system_prompt = rag.inject_into_system_prompt(results)
    print(system_prompt, "\n------------\n")
    # Request AI Response
    ai_response = api.chat_request(system=system_prompt, user=user_prompt)
    print(ai_response, "\n------------\n")
    # Form Final Chat Response
    output = rag.append_metadata_to_response(ai_response, results)
    print(output, "\n------------\n")
    return output

if __name__ == "__main__":
    run(user_prompt)