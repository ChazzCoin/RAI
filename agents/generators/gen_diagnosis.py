from dataset.intake.PDF_v1 import FPDF
from assistant import openai_client as api
from agents.prompts.diagnosis import DIAGNOSTIC_SYSTEM_PROMPT as sys_prompt

def run_manual_files(FILES: [str]):
    # Select the proper folder
    for file in FILES:
        try:
            content = FPDF(file_path=file).extract_text_from_pdf(file)
            results = api.chat_request(system=sys_prompt, user=content, model="gpt-4o-mini")
            print("-------")
            print(results)
            print("-------")
        except Exception as e:
            print(f"Error processing file: {file} with error", e)


if __name__ == "__main__":
    run_manual_files()