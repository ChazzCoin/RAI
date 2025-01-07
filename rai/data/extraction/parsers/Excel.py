import re
import csv
import json
import pandas as pd


def excel_to_json(excel_file_path, json_file_path=None):
    """
    Convert an Excel file into a JSON file where each sheet's content is
    converted to an array of JSON objects, with sheet names as keys in the list.

    Parameters:
        excel_file_path (str): Path to the input Excel file.
        json_file_path (str): (Optional) Path to the output JSON file.
                              If not provided, data is only returned.
    Returns:
        str or None: Returns the path to the JSON file if json_file_path is
                     provided and the operation is successful, otherwise None.
    """
    try:
        # Read the entire workbook
        workbook = pd.ExcelFile(excel_file_path)

        # List to hold all sheets' data
        all_sheets_data = []

        # Loop through each sheet in the workbook
        for sheet_name in workbook.sheet_names:
            # Read the sheet into a DataFrame
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name)

            # Convert any missing values to empty string, then cast all columns to string
            df = df.fillna('')
            df = df.astype(str)

            # Convert each row in the DataFrame to a dictionary
            sheet_data = df.to_dict(orient='records')

            # Append the sheet's data in the format "Sheet Name": sheet data
            all_sheets_data.append({sheet_name: sheet_data})

        # Write JSON to file if a path is provided
        if json_file_path:
            with open(json_file_path, mode='w', encoding='utf-8') as json_file:
                json.dump(all_sheets_data, json_file, indent=4)
            print(f"Excel file successfully converted to JSON. Saved to: {json_file_path}")
            return json_file_path

        # If no json_file_path, you can return the data as a Python object
        return all_sheets_data

    except Exception as e:
        print(f"Error occurred: {e}")
        return None

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







def remove_excess_whitespace(text):
    # Remove extra spaces and new lines
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    return cleaned_text

# Example usage
csv_file_path = '/Users/chazzromeo/Desktop/pcsc2024/pending/practice_schedules.xlsx'  # Input CSV file path
json_file_path = '/Users/chazzromeo/Desktop/pcsc2024/general/practice_schedules.json'  # Output JSON file path
# csv_to_json(csv_file_path, json_file_path)
excel_to_json(csv_file_path, json_file_path)
# # sheet_name = 'export (51)'
# records = extract_spreadsheet_records(csv_file_path)
# print(records)
#
# # Convert the spreadsheet to JSON
# json_data = extract_spreadsheet_text(csv_file_path)
# cleaned_data = remove_excess_whitespace(json_data)
# print(cleaned_data)
