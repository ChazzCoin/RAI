import docx

def word_to_txt_file(docx_file):
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
        return extracted_text
    except Exception as e:
        print(f"Error processing the Word document {docx_file}: {e}")
        return []
