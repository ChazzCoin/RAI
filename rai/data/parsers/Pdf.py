from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter, PDFPageAggregator
from pdfminer.layout import LAParams, LTImage, LTTextBox, LTTextLine, LTFigure
from pdfminer.pdfpage import PDFPage
import pytesseract
from io import BytesIO, StringIO
from PIL import Image
from pyxnat.core.uriutil import file_path
from rai.data.utilities.TextUtils import TextProcessor
import re
PDF_MODEL = lambda x: {}
PostProcessor = TextProcessor()

def only_spaces_and_newlines(text: str) -> bool:
    pattern = r'^[ \n]*$'
    return bool(re.match(pattern, text))

def list_of_strings_to_string(content: [str]) -> str:
    temp = ""
    for item in content:
        temp += " " + str(item)
    return str(temp).strip()

class FPDF:
    file_paths = []
    file_texts = [{}]

    def __init__(self, file_path):
        if OS.is_directory(file_path):
            temp = OS.get_files_in_directory(file_path)
            for t in temp:
                self.file_paths.append(f"{file_path}/{t}")
            print(self.file_paths)
        else:
            self.file_paths = [file_path]

    def run(self):
        for file_path in self.file_paths:
            try:
                text = self.extract_text_from_pdf(file_path)
                sents = self.post_process_text(text)
                cleaned = []
                for s in sents:
                    cleaned_s = PostProcessor.clean_text_for_openai_embedding(s)
                    cleaned.append(cleaned_s)
                full_text = list_of_strings_to_string(cleaned)
                for_ai = TextProcessor.split_text_to_sentences(str(full_text))
                j = {
                    "text": full_text,
                    "training": for_ai,
                    "file": file_path
                }
                self.file_texts.append(j)
            except Exception as e:
                print(f"Error: {e}")
        OS.save_dict_to_file("pdf_training_data", self.file_texts, file_path=OS.get_cwd())
        return self.file_texts

    def post_process_text(self, text_in:str) -> str:
        text_out = TextProcessor.split_text_to_sentences(text_in)
        return text_out

    @staticmethod
    def extract_text_from_pdf_old(path):
        try:
            # Class Setup
            rsrcmgr = PDFResourceManager()
            retstr = StringIO()
            laparams = LAParams()
            device = TextConverter(rsrcmgr, retstr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            # Configs
            password = ""
            maxpages = 0
            caching = True
            pagenos=set()

            # Extraction
            fp = open(path, 'rb')
            pdf_document = PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True)
            for page in pdf_document:
                interpreter.process_page(page)
                print(page.contents)

            text = retstr.getvalue()

            print("Character Count:", len(text))
            text_paragraphs = PostProcessor.split_text_to_paragraphs(text)
            print("Paragraphs Count:", len(text_paragraphs))

            def clean_paragraphs(paras):
                new_paragraphs = []
                if paras:
                    temp_p = ""
                    building = False
                    for paragraph in paras:
                        if len(paragraph) < 100:
                            if not building: building = True
                            temp_p = f"{temp_p} {paragraph}"
                        else:
                            if building:
                                if len(temp_p) > 100:
                                    new_paragraphs.append(PostProcessor.clean_text_for_openai_embedding(temp_p))
                                    temp_p = ""
                                    building = False
                            temp_p = f"{temp_p}\n{PostProcessor.clean_text_for_openai_embedding(paragraph)}"
                            new_paragraphs.append(temp_p)
                            temp_p = ""
                return new_paragraphs

            fp.close()
            device.close()
            retstr.close()
            return clean_paragraphs(text_paragraphs)
        except Exception as e:
            print(f"Error: {e}")
            return None

    @staticmethod
    def extract_text_from_pdf(file_path=None, file_data=None, bytes=None):
        """
        Extracts text from a PDF file given as raw byte data.

        :param file_data: The PDF file content as a raw byte string.
        :return: Extracted text as a string.
        """
        # Set up resource manager, output StringIO, and LAParams
        rsrcmgr = PDFResourceManager()
        retstr = StringIO()
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, laparams=laparams)

        # Use BytesIO to handle the bytes input as a stream
        fp = BytesIO(file_data) if file_data else bytes

        # Set up PDF interpreter
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # Extract text from each page
        for page in PDFPage.get_pages(fp, caching=True, check_extractable=True):
            interpreter.process_page(page)

        # Get the full text
        text = retstr.getvalue()

        # Close the resources
        fp.close()
        device.close()
        retstr.close()

        return text

    @staticmethod
    def extract_v2(file_path=None, file_data=None, file_bytes=None):
        # Create a PDF resource manager object that stores shared resources
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        # PDFPageAggregator gives us access to the page layout
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)

        # Decide how to get our file-like object
        if file_data: fp = BytesIO(file_data)
        elif file_bytes: fp = file_bytes
        elif file_path: fp = open(file_path, 'rb')
        else: return None

        interpreter = PDFPageInterpreter(rsrcmgr, device)

        pages_data = []
        page_number = 0

        for page in PDFPage.get_pages(fp, caching=True, check_extractable=True):
            page_number += 1

            # Process the page
            interpreter.process_page(page)
            layout = device.get_result()

            # Collect text and images for this page
            page_text = []
            page_images = []

            def parse_layout_objects(l_objs):
                """ Recursively parse the layout objects (text boxes, lines, images, figures). """
                for obj in l_objs:

                    # """ TEXT """
                    if isinstance(obj, (LTTextBox, LTTextLine)):
                        t = obj.get_text()
                        if not only_spaces_and_newlines(t):
                            page_text.append(t)
                   # """ IMAGE BYTES """
                    elif isinstance(obj, LTImage):
                        try:
                            img_data = obj.stream.get_data()
                            # # Convert raw bytes to a BytesIO stream
                            image_stream = BytesIO(img_data)

                            # Open the image with PIL
                            with Image.open(image_stream) as img:
                                # Perform OCR
                                extracted_text = pytesseract.image_to_string(image_stream)
                                page_images.append(extracted_text)
                        except Exception as e:
                            print(f"Error: {e}")
                    # """ NESTED OBJECTS/RECURSIVE """
                    elif isinstance(obj, LTFigure):
                        parse_layout_objects(obj._objs)

            # Parse all items in the layout
            parse_layout_objects(layout._objs)

            pages_data.append({
                "page_number": page_number,
                "text": page_text,
                "combined": " ".join(page_text),
                "images": page_images
            })
            print(pages_data)

        # Clean up
        fp.close()
        device.close()

        return pages_data



if __name__ == '__main__':
    from F import OS
    cwd = OS.get_cwd()
    file = "/Users/chazzromeo/Desktop/pcsc2024/general/2024_PCSC_Tournament_Philosophy___Policy_-_07.11.21_Final_(2).docx.pdf"
    result = FPDF.extract_v2(file_path=file)
    print(result)
    # file = f"{cwd}/../Utils/mlpython.pdf"
    # ps = FPDF(file).run()