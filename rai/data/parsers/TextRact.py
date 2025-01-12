import os
import logging
import textract
from textract.exceptions import (
    ExtensionNotSupported,
    ShellError
)
from F.LOG import Log
Log = Log("TextRact")

class TextExtractor:
    file_path: str
    def __init__(self, file_path: str, encoding='utf-8'):
        """
        Initializes the TextExtractor.

        Args:
            encoding (str): The text encoding to use. Default is 'utf-8'.
            logger (logging.Logger): Optional custom logger.
        """
        self.file_path = file_path
        self.encoding = encoding

    def extract_text(self):
        """
        Extracts text from the given file using textract.

        Args:
            filepath (str): Path to the file from which to extract text.

        Returns:
            str: Extracted text content.

        Raises:
            FileNotFoundError: If the file does not exist.
            TypeError: If the filepath is not a string.
            textract.exceptions.ExtensionNotSupported: If the file extension is unsupported.
            textract.exceptions.ShellError: If a shell error occurs during extraction.
            Exception: For any other exceptions not explicitly caught.
        """
        if not isinstance(self.file_path, str):
            Log.w(f'Invalid file path type: {type(self.file_path)}')
            return ""
        if not os.path.exists(self.file_path):
            Log.w(f'File not found: {self.file_path}')
            return ""
        Log.i(f'Starting text extraction from: {self.file_path}')
        try:
            text_bytes = textract.process(self.file_path, encoding=self.encoding)
            text = text_bytes.decode(self.encoding)
            Log.i(f'Text extraction successful from: {self.file_path}')
            return text
        except ExtensionNotSupported as e:
            Log.w(f'Unsupported file extension for file: {self.file_path}')
            return ""
        except ShellError as e:
            Log.w(f'Shell error during text extraction from {self.file_path}: {e}')
            return ""
        except Exception as e:
            Log.w( f'An unexpected error occurred during text extraction from {self.file_path}: {e}')
            return ""
