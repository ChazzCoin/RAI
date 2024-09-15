import pandas as pd
from config import default_file_path
from files.FilePath import FilePath
from files.save import DataSaver


def excel_to_txt_file(excel_file, output_text_file:FilePath):
    # Load the Excel file
    df = pd.read_excel(excel_file, engine='openpyxl')
    full_text = []
    for index, row in df.iterrows():
        full_text.append(" | ".join([str(value) for value in row]))
    # Write the extracted data to a text file
    DataSaver.save_txt(data=full_text, output=output_text_file)
    print(f"Data successfully extracted to {output_text_file}")

if __name__ == "__main__":
    # Example usage
    excel_file_path = "/Users/chazzromeo/Desktop/parkcitysoccer/PCSC 2024 Kickoff Camp.xlsx"
    output_text_file_path = f"{default_file_path()}/PCSC 2024 Kickoff Camp.txt"
    excel_to_txt_file(excel_file_path, output_text_file_path)
