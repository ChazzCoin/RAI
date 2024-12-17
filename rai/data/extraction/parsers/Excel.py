import pandas as pd
import csv
import json
import re

def excel_to_txt_file(excel_file):
    # Load the Excel file
    df = pd.read_excel(excel_file, engine='openpyxl')
    full_text = []
    for index, row in df.iterrows():
        full_text.append(" | ".join([str(value) for value in row]))
    return full_text

def csv_to_json(csv_file_path, json_file_path=None):
    """
    Convert a CSV file into a JSON file where each record is a separate JSON object.

    Parameters:
        csv_file_path (str): Path to the input CSV file.
        json_file_path (str): Path to the output JSON file.
    """
    try:
        # Open the CSV file
        with open(csv_file_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            # Read and store each row as a JSON object
            data = [str(row) for row in csv_reader]

        if json_file_path:
            # Write to the JSON file
            with open(json_file_path, mode='w') as json_file:
                json.dump(data, json_file, indent=4)

        print(f"CSV file successfully converted to JSON. Saved to: {json_file_path}")
        return json_file
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def convert_spreadsheet_to_json(file_path, sheet_name):
    # Read the specified sheet
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Clean up and organize the data (remove NaNs, reset index, etc.)
    df.fillna('', inplace=True)

    # Convert rows into a list of JSON objects
    records = []

    # Iterate through rows and structure data into dictionaries
    for _, row in df.iterrows():
        record = {}
        for column in df.columns:
            record[column] = row[column]
        records.append(record)

    return records

def extract_spreadsheet_records(file_path):
    # Read the entire spreadsheet
    spreadsheet = pd.ExcelFile(file_path)

    all_text = ''
    all_records = []
    # Iterate through all sheets
    for sheet_name in spreadsheet.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # Clean up and organize the data (remove NaNs, reset index, etc.)
        df.fillna('', inplace=True)

        records = []
        # Iterate through rows and structure data into dictionaries
        for _, row in df.iterrows():
            record = {}
            for column in df.columns:
                record[column] = row[column]
            records.append(record)
        all_records.append(records)

    return all_records

def extract_spreadsheet_text(file_path):
    # Read the entire spreadsheet
    spreadsheet = pd.ExcelFile(file_path)

    all_text = ''

    # Iterate through all sheets
    for sheet_name in spreadsheet.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # Clean up and organize the data (remove NaNs, reset index, etc.)
        df.fillna('', inplace=True)

        # Combine all text from the sheet into a single string
        sheet_text = ' '.join(df.astype(str).values.flatten())
        all_text += sheet_text + ' '

    return all_text

def remove_excess_whitespace(text):
    # Remove extra spaces and new lines
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    return cleaned_text

# Example usage
# csv_file_path = '/Users/chazzromeo/Desktop/pcsc2024/pending/194143_players_2024-10-02.csv'  # Input CSV file path
# json_file_path = '/Users/chazzromeo/Desktop/pcsc2024/general/194143_players_2024-10-02.json'  # Output JSON file path
# csv_to_json(csv_file_path, json_file_path)
# # sheet_name = 'export (51)'
# records = extract_spreadsheet_records(csv_file_path)
# print(records)
#
# # Convert the spreadsheet to JSON
# json_data = extract_spreadsheet_text(csv_file_path)
# cleaned_data = remove_excess_whitespace(json_data)
# print(cleaned_data)
