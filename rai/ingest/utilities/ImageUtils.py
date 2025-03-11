import base64
import os
from typing import Union, Optional
# For improved MIME type detection
import magic


class FileUtils:

    @staticmethod
    def open(file:str) -> Optional[bytes]:
        try:
            with open(file, "rb") as f:
                img_bytes = f.read()
            return img_bytes
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def save_base64_to_file(base64_str: str, output_path: str, overwrite: bool = False) -> Optional[str]:
        """
        Decodes a base64 string and saves it to a file.
        Args:
            base64_str (str): The base64 encoded string to decode.
            output_path (str): The file path where the decoded file will be saved.
            overwrite (bool): Whether to overwrite an existing file. Defaults to False.
        Returns:
            Optional[str]: The path to the saved file if successful, None otherwise.
        """
        if os.path.exists(output_path) and not overwrite:
            print(f"File '{output_path}' already exists and overwrite is set to False.")
            return None

        try:
            file_data = base64.b64decode(base64_str, validate=True)
        except base64.binascii.Error as e:
            print(f"Error decoding base64 string: {e}")
            return None

        try:
            with open(output_path, 'wb') as file:
                file.write(file_data)
            return output_path
        except IOError as e:
            print(f"Error writing file '{output_path}': {e}")
            return None

    @staticmethod
    def encode_to_base64(input_data: Union[str, bytes]) -> Optional[str]:
        """
        Encodes various input types (file path, bytes, base64 strings) into a standardized base64 string.
        Args: input_data (str | bytes): Can be a file path, raw bytes, or already base64-encoded string.
        Returns: str: Base64-encoded string of the input data.
        """
        # Check if the input is a valid file path
        if isinstance(input_data, str) and os.path.isfile(input_data):
            with open(input_data, 'rb') as file:
                file_bytes = file.read()
            return base64.b64encode(file_bytes).decode('utf-8')

        # Check if input_data is a base64-encoded string already
        if isinstance(input_data, str):
            try:
                # Attempt decoding to verify if it's valid base64
                base64.b64decode(input_data, validate=True)
                return input_data
            except base64.binascii.Error:
                # Not valid base64, treat as plain text
                file_bytes = input_data.encode('utf-8')
                return base64.b64encode(file_bytes).decode('utf-8')

        # If input_data is bytes, directly encode to base64
        if isinstance(input_data, bytes):
            return base64.b64encode(input_data).decode('utf-8')

        print("Input data type is unsupported.")
        return None

    @staticmethod
    def base64_to_bytes(base64_str: str) -> Optional[bytes]:
        """
        Converts a base64-encoded string to bytes.
        Args: base64_str (str): The base64 string to convert.
        Returns: Optional[bytes]: The decoded bytes, or None if decoding fails.
        """
        try:
            return base64.b64decode(base64_str, validate=True)
        except base64.binascii.Error as e:
            print(f"Error decoding base64 to bytes: {e}")
            return None

    @staticmethod
    def detect_file_format(file_bytes: bytes) -> str:
        """
        Detects the file format from the given byte string.
        Args: file_bytes (bytes): The byte string of the potential file.
        Returns: str: The file format (e.g., 'JPEG', 'PNG', 'GIF', 'PDF', 'DOCX', 'TXT', etc.) or 'Unknown'.
        """
        if not file_bytes: return 'Unknown'

        try:
            mime = magic.from_buffer(file_bytes, mime=True)
            mime_mapping = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/gif': 'GIF',
                'image/bmp': 'BMP',
                'image/tiff': 'TIFF',
                'image/webp': 'WEBP',
                'image/x-icon': 'ICO',
                'application/pdf': 'PDF',
                'application/msword': 'DOC',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
                'application/vnd.ms-excel': 'XLS',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
                'text/plain': 'TXT',
                'text/csv': 'CSV',
                'application/zip': 'ZIP',
                'application/json': 'JSON',
                'application/xml': 'XML',
                'audio/mpeg': 'MP3',
                'video/mp4': 'MP4',
            }
            return mime_mapping.get(mime, 'Unknown')
        except Exception as e:
            print(f"Error detecting file format: {e}")
            return 'Unknown'


# Example Usage:
if __name__ == "__main__":
    # with open("/Users/chazzromeo/Desktop/portal/docs/Neuro101.pdf", "rb") as f:
    #     img_bytes = f.read()

    detected_format = FileUtils.detect_file_format("/Users/chazzromeo/Desktop/portal/docs/Neuro101.pdf")
    print(f"Detected image format: {detected_format}")
