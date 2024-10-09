import pdfplumber
from files.save import DataSaver
from F import LIST
from dataset.intake.PDF_v1 import FPDF

"""
    ------------
"""

def pdf_to_txt_file(pdf_file, output_text_file:str):
    """
    Extracts text from a PDF document and saves it to a text file.
    Args:
        pdf_file (str): The path to the PDF document.
        output_text_file (str): The path to the output text file where extracted data will be saved.
    """
    try:
        # Initialize an empty string to collect the extracted text
        extracted_text = []
        # Open the PDF file
        with pdfplumber.open(pdf_file) as pdf:
            # Loop through each page of the PDF
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
        DataSaver.save_txt(data=extracted_text, output=output_text_file)
        print(f"Text successfully extracted to {output_text_file}")
    except Exception as e:
        print(f"Error processing the PDF document {pdf_file}: {e}")

def pdf_to_txt(pdf_file):
    """
    Extracts text from a PDF document and saves it to a text file.
    Args:
        pdf_file (str): The path to the PDF document.
        output_text_file (str): The path to the output text file where extracted data will be saved.
    """
    try:
        # Initialize an empty string to collect the extracted text
        extracted_text = []
        # Open the PDF file
        with pdfplumber.open(pdf_file) as pdf:
            # Loop through each page of the PDF
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
        print(f"Text successfully extracted pdf.")
        return LIST.to_str(extracted_text)
    except Exception as e:
        print(f"Error processing the PDF document {pdf_file}: {e}")
        return FPDF.extract_text_from_pdf(pdf_file)



if __name__ == "__main__":
    # from dataset.intake import PowerPoint
    # Example usage
    # pdf_file_path = "/Users/chazzromeo/Desktop/ussfTrainingData/us-soccer-player-development-framework-age-group-learning-plans.pdf"
    pdf_file_path = "/Users/chazzromeo/Desktop/ParkCityTrainingData/PCSCIndividualDevelopmentPlan11U12U.docx"
    # pdf_file = PowerPoint.convert_pptx_to_pdf(pdf_file_path)
    # output_text_file_path = f"{default_file_path()}/PCSC Player Handbook.txt"

    # pdf_to_txt_file(pdf_file_path, output_text_file_path)
    # text = pdf_to_txt(pdf_file_path)
    vision = VisionDataLoader(pdf_file_path)
    print(f"vision: {len(vision.data)}")

    # image = Image.open(io.BytesIO(vision[0]['image'][0]))

    # Display the image (this opens the image using the default image viewer)
    # image.show()

    # Optionally, save the image to a file
    # image.save('/Users/chazzromeo/Desktop/output_image.png')
    # Image.open(vision[0]['image'][0])