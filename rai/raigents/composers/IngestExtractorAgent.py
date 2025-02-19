from typing import Optional

from F import DICT, DATE, LIST
import nlp.Tokenizer
import nlp.Paragraphs
import nlp.Re
import nlp.Keywords
from nlp.ext import NLPAssistant
from rai.ingest.parsers.PdfDiver import RaiPdfDiver
from rai.ingest.utilities.TextUtils import TextProcessor, to_sentences
from rai.ingest.utilities.text_data import schedule_text
from rai.ingest.web.WebModels import PageAnalysisModel, FNLPAssistantModel, NLPAssistantModel, TextNLPAgentModel
from rai.raigents.base.BaseImageAgents.BaseImageAgent import RaiBaseImageAgent
from rai.raigents.base.BaseTextAgents.BaseTextAgent import RaiBaseTextAgent

DOC_SPLIT_SIZE = 10000

"""
 analysis
     1. Sentiment
     2. Document Type
     3. Syntactic Parsing
     4. Named Entity Recognition
     5. Part-of-Speech (POS) Tagging
     6. Relationship Extraction
     7. Topic
 enhancement
     1. RAG question generation
     2. Morphological Analysis & Lemmatization
     3. Coreference Resolution
     4. Text Classification & Categorization
     5. Semantic Role Labeling
     6. Contextual Metadata Tagging
     7. Paraphrasing & Rewriting

     ANALYZE IMAGE VIA AI
 """
DOC_SPLIT_SIZE = 10000

"""
url
file
bytes

"""


import os
import re
import json
from urllib.parse import urlparse

class DataTypeUtils:
    # Parent Type
    @staticmethod
    def is_url(data) -> bool:
        """
        Check if the given data is a URL.
        """
        if not isinstance(data, str):
            return False
        parsed = urlparse(data)
        return parsed.scheme in ("http", "https", "ftp") and bool(parsed.netloc)

    @staticmethod
    def is_file(data) -> bool:
        """
        Check if the given data is a path to an existing file.
        """
        if not isinstance(data, str):
            return False
        return os.path.isfile(data)

    @staticmethod
    def is_text(data) -> bool:
        """
        Determine if data is text content.
        We assume that if data is a string (and not a URL or a valid file path), it's text.
        """
        if isinstance(data, str):
            # If it doesn't look like a URL or an existing file, treat it as text content.
            return not DataTypeUtils.is_url(data) and not DataTypeUtils.is_file(data)
        return False

    @staticmethod
    def is_bytes(data) -> bool:
        """
        Check if the given data is of type bytes.
        """
        return isinstance(data, bytes)

    # Image Type
    @staticmethod
    def is_image(data) -> bool:
        """
        Check if the given data represents an image.
        It returns True if the data is detected as either PNG, JPG/JPEG, or has another common image extension.
        """
        if DataTypeUtils.is_png(data) or DataTypeUtils.is_jpg(data):
            return True
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.gif', '.bmp', '.tiff', '.jpeg']
        return False
    @staticmethod
    def is_png(data) -> bool:
        """
        Determine if the given data is a PNG image.
        For a filename, it checks the extension.
        For bytes, it checks for the PNG magic number.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext == '.png'
        elif isinstance(data, bytes):
            # PNG signature: 89 50 4E 47 0D 0A 1A 0A
            return data.startswith(b'\x89PNG\r\n\x1a\n')
        return False
    @staticmethod
    def is_jpg(data) -> bool:
        """
        Determine if the given data is a JPEG image.
        For a filename, it checks for .jpg or .jpeg extension.
        For bytes, it checks for JPEG file signature.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.jpg', '.jpeg']
        elif isinstance(data, bytes):
            # JPEG files typically start with FF D8
            return data.startswith(b'\xff\xd8')
        return False

    # Other Media Types
    @staticmethod
    def is_audio(data) -> bool:
        """
        Check if the given data represents an audio file based on common audio file extensions.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
        return False
    @staticmethod
    def is_video(data) -> bool:
        """
        Check if the given data represents a video file based on common video file extensions.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
        return False

    # File Type
    @staticmethod
    def is_pdf(data) -> bool:
        """
        Check if the given data represents a PDF file.
        For filenames, it checks the extension.
        For bytes, it looks for the PDF header (%PDF-).
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext == '.pdf'
        elif isinstance(data, bytes):
            return data.startswith(b'%PDF-')
        return False
    @staticmethod
    def is_html(data) -> bool:
        """
        Check if the given data represents HTML content.
        For filenames, it checks the extension (.html or .htm).
        For text content, it searches for HTML tags.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            if ext in ['.html', '.htm']:
                return True
            # Look for basic HTML tags in text content.
            return bool(re.search(r'<html.*?>', data, re.IGNORECASE))
        return False
    @staticmethod
    def is_excel(data) -> bool:
        """
        Check if the given data represents an Excel file.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.xls', '.xlsx']
        return False
    @staticmethod
    def is_json(data) -> bool:
        """
        Check if the given data is valid JSON.
        For strings and bytes, it attempts to load the JSON.
        """
        if isinstance(data, str):
            try:
                json.loads(data)
                return True
            except Exception:
                return False
        elif isinstance(data, bytes):
            try:
                json.loads(data.decode('utf-8'))
                return True
            except Exception:
                return False
        return False
    @staticmethod
    def is_jsonl(data) -> bool:
        """
        Check if the given data represents JSON Lines format.
        This expects multiple lines where each line is a valid JSON object.
        """
        def check_json_lines(text: str) -> bool:
            lines = text.strip().splitlines()
            if len(lines) < 2:
                return False
            for line in lines:
                try:
                    json.loads(line)
                except Exception:
                    return False
            return True

        if isinstance(data, str):
            return check_json_lines(data)
        elif isinstance(data, bytes):
            try:
                text = data.decode('utf-8')
                return check_json_lines(text)
            except Exception:
                return False
        return False
    @staticmethod
    def is_xml(data) -> bool:
        """
        Check if the given data represents XML content.
        For filenames, it checks the extension.
        For text or bytes, it looks for an XML declaration.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            if ext == '.xml':
                return True
            return data.lstrip().startswith('<?xml')
        elif isinstance(data, bytes):
            try:
                text = data.decode('utf-8')
                return text.lstrip().startswith('<?xml')
            except Exception:
                return False
        return False
    @staticmethod
    def is_word(data) -> bool:
        """
        Check if the given data represents a Word document.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext in ['.doc', '.docx']
        return False

    @staticmethod
    def is_pptx(data) -> bool:
        """
        Check if the given data represents a PowerPoint file (.pptx).
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext == '.pptx'
        return False
    @staticmethod
    def is_txt(data) -> bool:
        """
        Check if the given data represents a plain text file.
        """
        if isinstance(data, str):
            ext = os.path.splitext(data)[1].lower()
            return ext == '.txt'
        return False


class IngestExtractorAgent:
    cleaner = TextProcessor()  # Assumes a TextProcessor with a TEXT_CLEANER and content_splitter is defined

    data_in = None
    data_type = None

    book = {}

    class Text:
        metadata = "metadata"
        industry = "industry"
        form_extractor = "form_extractor"
        urls = "urls"
        events = "events"
        contacts = "contacts"
        locations = "locations"

    class Image:
        text_extractor = "text_extractor"
        table_extractor = "table_extractor"
        form_extractor = "form_extractor"

    @classmethod
    def load_data(cls, data):
        self = cls()
        self.data_in = data
        self.data_type = self.determine_data_type(data)
        return self

    def run(self):
        if not self.data_in: return
        if self.data_type == 'URL':
            pass
        elif self.data_type == 'PDF':
            diver = RaiPdfDiver(self.data_in)
            self.book = diver.run()

    @staticmethod
    def extract_from_images(name, images):
        results = []
        for image in images:
            text = RaiBaseImageAgent.generate(name, image)
            results.append(text)
        return results

    @staticmethod
    def extracts_from_images(*names, images):
        results = []
        for image in images:
            text = RaiBaseImageAgent.generates(*names, image)
            results.append(text)
        return results


    # -------------------------------
    # Master methods to run the analysis
    # -------------------------------
    @staticmethod
    def determine_data_type(data) -> str:
        """
        Determine the data type of the given input by utilizing the DataTypeUtils class.

        The function checks in the following order:
          1. URL: If the data is a URL.
          2. File: If the data is a file path, then further inspect its file type.
          3. Text: If the data is a plain text string (and not a URL or file).
          4. Bytes: If the data is bytes, then inspect for common binary signatures.

        Returns:
            A string describing the determined data type.
        """
        dt = DataTypeUtils

        # 1. Check if the data is a URL.
        if dt.is_url(data):
            return "URL"

        # 2. Check if the data is a file path.
        elif dt.is_file(data):
            # File type determination based on extension/signature.
            if dt.is_image(data):
                if dt.is_png(data):
                    return "Image (PNG)"
                elif dt.is_jpg(data):
                    return "Image (JPG)"
                else:
                    return "Image (Other Format)"
            elif dt.is_pdf(data):
                return "PDF"
            elif dt.is_html(data):
                return "HTML"
            elif dt.is_excel(data):
                return "Excel"
            elif dt.is_json(data):
                return "JSON"
            elif dt.is_jsonl(data):
                return "JSONL"
            elif dt.is_xml(data):
                return "XML"
            elif dt.is_word(data):
                return "Word Document"
            elif dt.is_pptx(data):
                return "PowerPoint"
            elif dt.is_txt(data):
                return "Text"
            elif dt.is_audio(data):
                return "Audio"
            elif dt.is_video(data):
                return "Video"
            else:
                return "File (Unknown Format)"

        # 3. Check if the data is plain text content.
        elif dt.is_text(data):
            # Even though it's text, it might represent structured data.
            if dt.is_json(data):
                return "JSON (Text Content)"
            elif dt.is_jsonl(data):
                return "JSONL (Text Content)"
            elif dt.is_html(data):
                return "HTML (Text Content)"
            elif dt.is_xml(data):
                return "XML (Text Content)"
            else:
                return "Text Content"

        # 4. Check if the data is bytes (binary data).
        elif dt.is_bytes(data):
            if dt.is_png(data):
                return "Image (PNG Bytes)"
            elif dt.is_jpg(data):
                return "Image (JPG Bytes)"
            elif dt.is_pdf(data):
                return "PDF (Bytes)"
            elif dt.is_json(data):
                return "JSON (Bytes)"
            elif dt.is_xml(data):
                return "XML (Bytes)"
            else:
                return "Bytes Data"

        # Fallback if no type could be determined.
        else:
            return "Unknown Data Type"





if __name__ == "__main__":
    agent = IngestExtractorAgent()
    page_result = agent.execute(content=schedule_text)
    print(page_result)
