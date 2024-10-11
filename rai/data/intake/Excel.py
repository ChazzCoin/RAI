import pandas as pd

def excel_to_txt_file(excel_file):
    # Load the Excel file
    df = pd.read_excel(excel_file, engine='openpyxl')
    full_text = []
    for index, row in df.iterrows():
        full_text.append(" | ".join([str(value) for value in row]))
    return full_text
