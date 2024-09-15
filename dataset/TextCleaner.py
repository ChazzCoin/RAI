import re
import numpy as np
from FNLP.Language import Sentences
import unicodedata

from F.LOG import Log

from files.FilePath import FilePath

Log = Log("TextCleaner")

class TextCleaner:
    def __init__(self):
        self.unicode_replacements = {
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2026': '...',  # Ellipsis
            '\u00e9': 'e',  # é to e
            # Add more replacements as needed
        }
        self.title_pattern = re.compile(r'\b(' + '|'.join([
            'Mr\.', 'Mrs\.', 'Miss\.', 'Ms\.', 'Dr\.', 'Prof\.', 'Capt\.', 'Col\.', 'Gen\.', 'Lt\.', 'Maj\.', 'Sgt\.',
            'Adm\.', 'Cpl\.', 'Rev\.', 'Sen\.', 'Rep\.', 'Gov\.', 'Pres\.', 'Rt\.', 'Hon\.', 'Cmdr\.', 'Amb\.', 'Sec\.',
            'Dir\.',  # Add any additional titles as necessary
        ]) + r')\b')

    def clean_text(self, text):
        one = self.double_space_to_single_cleaner(text)
        two = self.unicode_cleaner(one)
        three = self.quote_cleaner(two)
        four = self.clean_sentence(three)
        return four

    def double_space_to_single_cleaner(self, text: str) -> str:
        """Replace double spaces with single space and tab with space."""
        return text.replace("  ", " ").replace("\t", " ")

    def unicode_cleaner(self, text: str) -> str:
        """Remove or replace unicode characters for proper AI training."""
        for unicode_char, ascii_char in self.unicode_replacements.items():
            text = text.replace(unicode_char, ascii_char)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        return text

    def quote_cleaner(self, text: str) -> str:
        """Replace or remove quotes appropriately for AI training."""
        text = text.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
        text = re.sub(r'(^\s*"\s*)|(\s*"\s*$)', '', text)
        text = re.sub(r'"\s*,', ',', text)
        text = re.sub(r'\s*"\s*', ' ', text)
        text = re.sub(r'http\s*:\s*//', 'http://', text, flags=re.IGNORECASE)
        return text.strip()

    def remove_period_from_titles(self, text):
        """Remove the period from common titles in the text."""
        # Create a regex pattern to match any of the titles with a period
        title_pattern = re.compile(r'\b(' + '|'.join([re.escape(title) for title in self.title_pattern]) + r')\b')
        # Replace periods from the titles
        def replace_period(match):
            return match.group(0).replace('.', '')
        return title_pattern.sub(replace_period, text)

    @staticmethod
    def clean_sentence(sentence):
        # Remove unnecessary characters and normalize spaces
        sentence = re.sub(r'\s+', ' ', sentence)  # Replace multiple spaces with a single space
        sentence = re.sub(r'\s*\(\s*', '(', sentence)  # Normalize spaces around parentheses
        sentence = re.sub(r'\s*\)\s*', ') ', sentence)
        sentence = re.sub(r'\s*:\s*', ': ', sentence)
        sentence = re.sub(r' +', ' ', sentence)  # Remove multiple spaces
        sentence = sentence.strip()  # Remove leading and trailing spaces

        # Fix common misspellings and formatting issues
        sentence = re.sub(r'\bModdel\b', 'Model', sentence)
        sentence = re.sub(r'\bColorad\b', 'Colorado', sentence)
        sentence = re.sub(r'\bcorporat\b', 'corporate', sentence)
        sentence = re.sub(r'\bDenve\b', 'Denver', sentence)
        sentence = re.sub(r'\bGarret Modde\b', 'Garrett Model', sentence)
        sentence = re.sub(r'\bBoulde\b', 'Boulder', sentence)
        sentence = re.sub(r'\bdisclaime\b', 'disclaimer', sentence)
        sentence = re.sub(r'\bFiled on\b', 'filed on', sentence)
        sentence = re.sub(r'\bPhotovoltaic Devic\b', 'Photovoltaic Device', sentence)
        sentence = re.sub(r'\bPatent\b', 'Patent.', sentence)
        sentence = re.sub(r'\bPhotovoltaic Devic\b', 'Photovoltaic Device', sentence)
        sentence = re.sub(r'\bApplic\b', 'Applicant', sentence)
        sentence = re.sub(r'\binventor\b', 'Inventor', sentence)
        sentence = re.sub(r'\bAssignee\b', 'Assignee:', sentence)
        sentence = re.sub(r'\bfield\b', 'Field', sentence)
        sentence = re.sub(r'\bapplication\b', 'Application', sentence)
        sentence = re.sub(r'\bsearch\b', 'Search', sentence)
        sentence = re.sub(r'\bpublication\b', 'Publication', sentence)
        sentence = re.sub(r'\bAttorney\b', 'Attorney', sentence)
        sentence = re.sub(r'\bAgent\b', 'Agent', sentence)
        sentence = re.sub(r'\bPrimary Examiner\b', 'Primary Examiner:', sentence)
        sentence = re.sub(r'\bFig\b', 'Figure', sentence)
        sentence = re.sub(r'\bLe\b', 'le', sentence)
        sentence = re.sub(r'\be\b', 'e', sentence)
        sentence = re.sub(r'\bo\b', 'o', sentence)
        sentence = re.sub(r'\ba\b', 'a', sentence)
        sentence = re.sub(r'\bnew\b', 'new', sentence)
        sentence = re.sub(r'\bfollow\b', 'follow', sentence)
        sentence = re.sub(r'\bdate\b', 'Date', sentence)
        sentence = re.sub(r'\btitle\b', 'Title', sentence)
        sentence = re.sub(r'\bNumber\b', 'Number', sentence)
        sentence = re.sub(r'\bApp\b', 'Application', sentence)
        sentence = re.sub(r'\bFiled\b', 'filed', sentence)
        sentence = re.sub(r'\bDated\b', 'dated', sentence)
        sentence = re.sub(r'\bdated\b', 'dated', sentence)
        sentence = re.sub(r'\bTherm\b', 'therm', sentence)
        sentence = re.sub(r'\bZero\b', 'zero', sentence)
        sentence = re.sub(r'\bLambe\b', 'lambe', sentence)
        sentence = re.sub(r'\bLebedev\b', 'lebedev', sentence)
        sentence = re.sub(r'\bHaisch\b', 'haisch', sentence)
        sentence = re.sub(r'\bL\b', 'le', sentence)
        sentence = re.sub(r'\bLambe\b', 'lambe', sentence)
        sentence = re.sub(r'\bGarret Modde\b', 'Garrett Moddel', sentence)
        return sentence

    def pipeline_basic_cleaning(self, text: str) -> str:
        """Run a basic cleaning pipeline on the text."""
        text = self.remove_period_from_titles(text)
        text = self.double_space_to_single_cleaner(text)
        text = self.unicode_cleaner(text)
        text = self.quote_cleaner(text)
        return text

    def pipeline_full_cleaning(self, text: str) -> str:
        """Run a full cleaning pipeline on the text."""
        text = self.pipeline_basic_cleaning(text)

        text = self.sentence_cleaner(text)
        return text

    def clean_training_data(self, sentences: list) -> list:
        """Clean a list of sentences for AI training."""
        return [self.sentence_cleaner(sentence) for sentence in sentences]

    @staticmethod
    def clean_text_for_openai_embedding(text: str, max_length: int = None, replace_unsupported: bool = True) -> str:
        """
        Cleans and filters out any characters that can't be embedded using OpenAI from a string.
        - Removes non-printable and control characters.
        - Filters out excessive whitespace and punctuation issues.
        - Normalizes text to NFC form (canonical decomposition followed by canonical composition).
        - Optionally replaces unsupported symbols like emojis with a placeholder or removes them.
        - Truncates text if it exceeds the max_length.

        :param text: The input string to clean.
        :param max_length: Optional maximum length to truncate the cleaned string.
        :param replace_unsupported: If True, replaces unsupported symbols with '[unsupported]'. If False, removes them.
        :return: A cleaned and filtered string that can be embedded using OpenAI.
        :raises TextCleaningError: If any cleaning step fails.
        """
        try:
            # Validate input
            if not isinstance(text, str):
                Log.e("Input must be a string.")
                return text
            Log.i(f"Starting text cleaning. Original length: {len(text)}")
            # Step 1: Normalize the text to Unicode NFC form (for consistent representation)
            try:
                normalized_text = unicodedata.normalize('NFC', text)
            except Exception as e:
                Log.e(f"Unicode normalization failed: {e}")
                return text
            # Step 2: Remove non-printable and invisible control characters
            try:
                cleaned_text = ''.join(char for char in normalized_text if
                                       char.isprintable() and not unicodedata.category(char).startswith('C'))
            except Exception as e:
                Log.e(f"Removing non-printable characters failed: {e}")
                return normalized_text
            # Step 3: Handle unsupported characters (e.g., emojis or other symbols)
            if replace_unsupported:
                # Replace emojis or unsupported symbols with '[unsupported]'
                cleaned_text = re.sub(r'[\U00010000-\U0010FFFF]+', '[unsupported]', cleaned_text)
            else:
                # Remove unsupported symbols (such as emojis)
                cleaned_text = re.sub(r'[\U00010000-\U0010FFFF]+', '', cleaned_text)
            # Step 4: Replace excessive punctuation (e.g., "...", "!!!", "???" -> single punctuation)
            cleaned_text = re.sub(r'([!?.,])\1+', r'\1', cleaned_text)
            # Step 5: Replace multiple spaces, newlines, or tabs with a single space
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            Log.i(f"Text cleaned. Length after cleaning: {len(cleaned_text)}")
            # Step 6: Truncate the text if it exceeds the max_length
            if max_length and len(cleaned_text) > max_length:
                cleaned_text = cleaned_text[:max_length].strip()
                Log.i(f"Text truncated to max length: {max_length}")
            Log.s(f"Final cleaned text length: {len(cleaned_text)}")
            return cleaned_text
        except Exception as e:
            Log.e(f"Unexpected error during text cleaning: {e}")
            return text

    @staticmethod
    def clean_text(text):
        # Remove non-relevant sections like headers, page numbers, etc.
        text = re.sub(r'--- Page \d+ ---', '', text)  # Remove page headers
        text = re.sub(r'\s+', ' ', text)  # Remove excessive whitespace
        text = text.strip()  # Strip leading and trailing whitespace
        return text

    @staticmethod
    def to_sentences(text, toString: bool = False):
        # Split text into sentences for embedding
        # sentences = re.split(r'(?<=[.!?]) +', text)
        cleaned_sentences = Sentences.to_sentences(content=text, combineQuotes=True)
        # Clean each sentence
        # cleaned_sentences = [clean_text(sentencestwo) for sentence in sentences if sentence]
        if toString:
            return str(cleaned_sentences)
        else:
            return cleaned_sentences

    @staticmethod
    def clean_nan_in_embeddings(embeddings):
        valid_embeddings = []
        for emb in embeddings:
            if not np.isnan(emb).any():
                valid_embeddings.append(emb)
        return valid_embeddings

    @staticmethod
    def process_file(file_path):
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        # Clean and preprocess the text
        return TextCleaner.to_sentences(text)

    @staticmethod
    def to_paragraphs(text):
        # Split the text by two or more newlines
        paragraphs = text.strip().split('\n\n')
        # Strip each paragraph of leading/trailing whitespace and filter out empty paragraphs
        paragraphs = [para.strip() for para in paragraphs if para.strip()]
        return paragraphs

    @staticmethod
    def to_paragraphs_with_min_max(text, min_length=1000, max_length=4000):
        # Split the text into paragraphs by double newline characters
        paragraphs = text.split('\n\n')
        # Strip leading/trailing whitespace from each paragraph
        paragraphs = [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]

        result = []
        buffer = ""

        for paragraph in paragraphs:
            # Add the buffer content to the current paragraph if buffer exists
            paragraph = buffer + paragraph
            buffer = ""

            # If the paragraph exceeds the max_length, split it up
            while len(paragraph) > max_length:
                result.append(paragraph[:max_length].strip())
                paragraph = paragraph[max_length:]

            # Add the remainder of the paragraph to buffer if less than min_length
            if len(paragraph) < min_length:
                buffer = paragraph
            else:
                result.append(paragraph)

        # Append any remaining buffer to the last paragraph or create a new one
        if buffer:
            if result and len(result[-1]) < min_length:
                result[-1] += " " + buffer
            else:
                result.append(buffer)

        return result

    @staticmethod
    def extract_text_between(text, start, stop):
        """
        Extracts the text between the given start and stop strings.
        :param text: The full text to extract from.
        :param start: The starting string.
        :param stop: The stopping string.
        :return: Text between start and stop, or an empty string if not found.
        """
        # Find the start position
        start_index = text.find(start)
        if start_index == -1:
            return "Start string not found."
        # Move the index to the end of the start string
        start_index += len(start)
        # Find the stop position
        stop_index = text.find(stop, start_index)
        if stop_index == -1:
            return "Stop string not found."
        # Extract and return the text between start and stop
        return text[start_index:stop_index].strip()


if __name__ == '__main__':
    from files.read import read_file
    text = read_file(FilePath(FilePath.PENDING).temp_add("barrowneuro", "barrowneuro-12.txt"))
    new_text = TextCleaner.extract_text_between(text, "Contact Us", "Social Media")
    print(new_text)