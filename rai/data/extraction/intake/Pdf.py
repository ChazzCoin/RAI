# import pdfplumber
# from F import LIST
# from rai.data.intake.PDF_v1 import FPDF
#
# def pdf_to_txt(pdf_file):
#     """
#     Extracts text from a PDF document and saves it to a text file.
#     Args:
#         pdf_file (str): The path to the PDF document.
#         output_text_file (str): The path to the output text file where extracted data will be saved.
#     """
#     try:
#         # Initialize an empty string to collect the extracted text
#         extracted_text = []
#         # Open the PDF file
#         with pdfplumber.open(pdf_file) as pdf:
#             # Loop through each page of the PDF
#             for page_num, page in enumerate(pdf.pages):
#                 text = page.extract_text()
#                 if text:
#                     extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
#         print(f"Text successfully extracted pdf.")
#         return LIST.to_str(extracted_text)
#     except Exception as e:
#         print(f"Error processing the PDF document {pdf_file}: {e}")
#         return FPDF.extract_text_from_pdf(pdf_file)
#
#
