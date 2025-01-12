from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import BytesIO, StringIO

from rai.data.utilities.TextUtils import TextProcessor

PDF_MODEL = lambda x: {}
PostProcessor = TextProcessor()

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
    def extract_text_from_pdf(path):
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
    def extract_text_from_pdf_bytes(file_data):
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
        fp = BytesIO(file_data)

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


if __name__ == '__main__':
    from F import OS
    cwd = OS.get_cwd()
    file = "/Users/chazzromeo/Desktop/ussf2024/player_dev_framework.pdf"
    result = FPDF.extract_text_from_pdf(file)
    # print(result)
    # file = f"{cwd}/../Utils/mlpython.pdf"
    # ps = FPDF(file).run()