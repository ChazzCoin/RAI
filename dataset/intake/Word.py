import docx

from files.FilePath import FilePath
from files.save import DataSaver


def word_to_txt_file(docx_file, output_text_file:FilePath):
    """
    Extracts text from a Microsoft Word document and saves it to a text file.
    Args:
        docx_file (str): The path to the Word document.
        output_text_file (str): The path to the output text file where extracted data will be saved.
    """
    try:
        # Load the Word document
        doc = docx.Document(docx_file)
        # Extract text from the document
        extracted_text = []
        for paragraph in doc.paragraphs:
            extracted_text.append(paragraph.text)
        # Write the extracted text to the output text file
        DataSaver.save_txt(data=extracted_text, output=output_text_file)
        # with open(output_text_file, "w", encoding="utf-8") as f:
        #     f.write("\n".join(extracted_text))
        print(f"Text successfully extracted to {output_text_file}")
    except Exception as e:
        print(f"Error processing the Word document {docx_file}: {e}")

if __name__ == "__main__":
    # Example usage
    word_file_path = "your_document.docx"
    output_text_file_path = "output_text.txt"
    word_to_txt_file(word_file_path, output_text_file_path)
