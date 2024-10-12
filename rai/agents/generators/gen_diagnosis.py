from rai.files.intake import FPDF
from rai.assistant import openai_client as api
from rai.agents.prompts.diagnosis import DIAGNOSTIC_SYSTEM_PROMPT as sys_prompt

def run_manual_files(FILES: [str]):
    # Select the proper folder
    for file in FILES:
        try:
            content = FPDF(file_path=file).extract_text_from_pdf(file)
            results = api.openai_generate(system_prompt=sys_prompt, user_prompt=content, model="gpt-4o-mini")
            print("-------")
            print(results)
            print("-------")
        except Exception as e:
            print(f"Error processing file: {file} with error", e)


if __name__ == "__main__":
    run_manual_files()