import re
from urllib.parse import urlparse

from F.LOG import Log

from rai.ingest.utilities.TextUtils import TextProcessor
from rai.ingest.web.RaiUrl import remove_non_printable_ascii

Log = Log("WebMaster")
class WebBaseHelper(TextProcessor):
    base_url: str = ""
    @staticmethod
    def clean_text(text: str) -> str:
        text = remove_non_printable_ascii(text)
        return ' '.join(text.split())

    @staticmethod
    def is_within_base_url(base_url, candidate_url: str) -> bool:
        parsed_base = urlparse(str(base_url))  # ensure string
        parsed_candidate = urlparse(candidate_url)
        return parsed_candidate.netloc == parsed_base.netloc

    @staticmethod
    def refine_text_content(content):
        """
        Remove unnecessary sections like footers, social media links, copyrights, and clean the text content.
        """
        # Define some patterns for sections to be ignored
        unwanted_patterns = [
            r'(\s|^)Social Media\s?.*',  # Matches "Social Media" and the text after
            r'(\s|^)Copyright.*',  # Matches "Copyright" and the text after
            r'(\s|^)Follow us.*',  # Matches "Follow us" sections
            r'(\s|^)Share.*',  # Matches "Share" links/buttons
            r'(\s|^)Subscribe.*',  # Matches "Subscribe" sections
            r'(\s|^)Cookie.*',  # Matches "Cookie" banners
            r'(\s|^)Terms of.*',  # Matches "Terms of" sections
            r'(\s|^)Privacy Policy.*',  # Matches "Privacy Policy" sections
            r'(\s|^)Related Articles.*',  # Matches "Related Articles" sections
        ]
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        # Optionally remove non-printable characters or extra white spaces
        content = remove_non_printable_ascii(content)
        content = re.sub(r'\s+', ' ', content).strip()  # Normalize white space

        return content
