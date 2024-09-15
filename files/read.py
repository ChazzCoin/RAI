import os
import csv
import logging
from dataset.intake.Pdf import pdf_to_txt
from docx import Document as DocxDocument
from openpyxl import load_workbook
from pptx import Presentation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def read_file(file_path):
    """
    Opens a file and returns its contents as a string, supporting various file formats.
    Supported file types: .txt, .pdf, .docx, .xlsx, .pptx, .csv.

    :param file_path: The path to the file.
    :return: The file contents as a string.
    :raises ValueError: If the file format is unsupported or reading fails.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == '.txt':
            return _read_txt(file_path)
        elif file_ext == '.pdf':
            return _read_pdf(file_path)
        elif file_ext == '.docx':
            return _read_docx(file_path)
        elif file_ext == '.xlsx':
            return _read_xlsx(file_path)
        elif file_ext == '.pptx':
            return _read_pptx(file_path)
        elif file_ext == '.csv':
            return _read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        raise ValueError(f"Failed to read the file: {e}")


# Helper functions for different file formats

def _read_txt(file_path):
    """Reads and returns the contents of a .txt file."""
    logging.info(f"Reading TXT file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def _read_pdf(file_path):
    """Reads and returns the text contents of a .pdf file."""
    logging.info(f"Reading PDF file: {file_path}")
    text = []
    with open(file_path, 'rb') as file:
        reader = pdf_to_txt(file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text.append(page.extract_text())
    return '\n'.join(text)


def _read_docx(file_path):
    """Reads and returns the text contents of a .docx file."""
    logging.info(f"Reading DOCX file: {file_path}")
    doc = DocxDocument(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])


def _read_xlsx(file_path):
    """Reads and returns the contents of an .xlsx file."""
    logging.info(f"Reading XLSX file: {file_path}")
    workbook = load_workbook(file_path, read_only=True)
    contents = []
    for sheet in workbook:
        contents.append(f"Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            contents.append('\t'.join([str(cell) for cell in row]))
    return '\n'.join(contents)


def _read_pptx(file_path):
    """Reads and returns the text contents of a .pptx file."""
    logging.info(f"Reading PPTX file: {file_path}")
    prs = Presentation(file_path)
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return '\n'.join(text)


def _read_csv(file_path):
    """Reads and returns the contents of a .csv file."""
    logging.info(f"Reading CSV file: {file_path}")
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        return '\n'.join([','.join(row) for row in reader])


# Example usage
if __name__ == '__main__':
    file_path = "/path/to/your/file"
    try:
        content = read_file_contents(file_path)
        print(f"Contents of {file_path}:\n{content}")
    except Exception as e:
        print(f"An error occurred: {e}")
