import json, re
from assistant import openai_client

RoleParkCitySoccerClub = "You are a knowledgeable assistant for the Park City Soccer Club, providing information about soccer programs and club activities."

Dataset_Format = lambda system: {"messages": [{"role": "system", "content": {system} }, {"role": "user", "content": "Question from the raw contents?"}, {"role": "assistant", "content": "Answer to the question..."}]}

System_Prompt = lambda role: f"""
You are now my personal AI Training Assistant. I will provide you with raw datasets and you will do the following.

1. You will clean the dataset by removing any missing values, duplicates, and outliers.
2. You will read the data and you will come up with a list of questions which you will provide VERY DETAILED, LONG, answers for.
3. You will reformat and return the list of questions/answers using the jsonl format to fine-tune using openai.
4. Only return the jsonl data for training and you will validate that the jsonl data coming back is complete and valid.
5. System Prompt to use in training data: "You are a knowledgeable assistant for the Organization, providing information about all information, details and activities involving the organization."
Example Response Format: 
```jsonl
{Dataset_Format(role)}
```
"""

def __base_save(json_lines, output_file):
    with open(output_file, 'a') as file:
        for json_line in json_lines:
            try:
                # Validate each line as JSON and remove any trailing commas
                json_obj = json.loads(json_line)
                print(f"Saving Jsonl File With: {json_obj}")
                # Write valid JSON objects to file, each on a new line
                file.write(json.dumps(json_obj) + '\n')
            except json.JSONDecodeError:
                print(f"Invalid JSON line skipped: {json_line}")

def pipeline_convert_raw_text_to_jsonl_dataset(raw_text, output_file, role: str = RoleParkCitySoccerClub):
    json_data = request_jsonl_formatting_from_ai(raw_text, role)
    save_jsonl_response(json_data, output_file)

def request_jsonl_formatting_from_ai(raw_text: str, role: str = RoleParkCitySoccerClub):
    return openai_client.chat_request(System_Prompt(role), raw_text, model="gpt-4o-mini")

def save_jsonl_response(jsonl_string, output_file):
    if jsonl_string.__contains__('jsonl'):
        save_jsonl_format(jsonl_string, output_file)
    else:
        json_lines = jsonl_string.strip().split("\n")
        __base_save(json_lines, output_file)
    verify_and_clean_jsonl(output_file)


def save_jsonl_format(jsonl_string: str, filename: str):
    print("Saving JSONL formatted string to file...")
    # Replace single quotes with double quotes to form a valid JSON string

    try:
        jsonl_string = jsonl_string.replace("```jsonl\n", '').replace("```", '')
        # parsed_json = json.loads(jsonl_string)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    # Open the file in write mode and save as JSONL
    with open(filename, 'w') as jsonl_file:
        # Write each message as a separate line in JSONL format
        # for message in parsed_json['messages']:
        jsonl_file.write(jsonl_string)

def extract_jsonl(data_string, output_file):
    # Regular expression to find JSON-like patterns
    jsonl_pattern = r'\{.*?\}\n'
    # Find all matching JSONL data in the string
    jsonl_matches = re.findall(jsonl_pattern, data_string, re.DOTALL)
    # Save the extracted data to a JSONL file
    __base_save(jsonl_matches, output_file)
    return jsonl_matches


def verify_and_clean_jsonl(input_file):
    fixed_lines = []
    output_file = input_file.replace(".jsonl", "-cleaned.jsonl")

    with open(input_file, 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        try:
            # Try to load the line as JSON
            json_obj = json.loads(line.strip())
            # If successful, append to the fixed lines list
            fixed_lines.append(json.dumps(json_obj))
        except json.JSONDecodeError:
            print(f"Error in line {i + 1}: {line.strip()}")
            # Attempt to fix common issues (e.g., trailing commas, extra characters)
            fixed_line = line.strip().rstrip(',')
            try:
                json_obj = json.loads(fixed_line)
                fixed_lines.append(json.dumps(json_obj))
                print(f"Fixed line {i + 1}")
            except json.JSONDecodeError:
                print(f"Unfixable line {i + 1}: {line.strip()}")

    # Save the fixed lines to a new file
    with open(output_file, 'w') as fixed_file:
        for fixed_line in fixed_lines:
            fixed_file.write(fixed_line + '\n')

    print(f"Verification and fixing completed. Fixed file saved as: {output_file}")