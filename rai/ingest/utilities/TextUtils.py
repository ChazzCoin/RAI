import re
import unicodedata

import tiktoken
from F import MATH, LIST, DICT
from F.LOG import Log
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rai.ingest.utilities.CompareUtils import DictComparator, StringComparator
from rai.internal.registries import RaiRegistry

Log = Log("TextCleaner")


SENTENCE_ENDERS = ['.', '?', '!']
QUOTES_ENCODINGS = [b'\xe2\x80\x9e', b'\xe2\x80\x9f', b'\xe2\x80\x9d', b'\xe2\x80\x9c']

ALPHABET_DICT_PAIRS = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G", "h": "H",
                       "i": "I", "j": "J", "k": "K", "l": "L", "m": "M", "n": "N", "o": "O", "p": "P",
                       "q": "Q", "r": "R", "s": "S", "t": "T", "u": "U", "v": "V", "w": "W", "x": "X",
                       "y": "Y", "z": "Z" }

GET_CAPITAL_FROM_LOWER = lambda lowerChar: DICT.get(lowerChar, ALPHABET_DICT_PAIRS, default=False)
GET_LOWER_FROM_CAPITAL = lambda capitalChar: DICT.get_key(capitalChar, ALPHABET_DICT_PAIRS, default=False)
GET_OPPOSITE_LOWER_OR_UPPER = lambda char: GET_CAPITAL_FROM_LOWER(char) if str(char).islower() else GET_LOWER_FROM_CAPITAL(char)

ALPHABET_LOWER = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
                  "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
ALPHABET_UPPER = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
                  "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
ALPHABET_ALL = ALPHABET_LOWER + ALPHABET_UPPER
NUMBERS_SINGLE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

SUMMARY = lambda first, middle, last: f"{first} {middle} {last}"

@RaiRegistry.register("processor", name="code")
class CodeProcessor:
    def split_swift_sections(self, code: str):
        """Extract Swift classes and functions."""
        return self.split_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*{",
            method_pattern=r"func\s+\w+\s*\(.*?\)\s*(->.*)?\s*{"
        )
    def split_python_sections(self, code: str):
        """Extract Python classes and functions."""
        return self.split_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*\(?.*?\)?:",
            method_pattern=r"def\s+\w+\s*\(.*?\)\s*:"
        )
    def split_java_kotlin_sections(self, code: str):
        """Extract Java/Kotlin classes and methods."""
        return self.split_classes_and_methods(
            code,
            class_pattern=r"(public|private|protected)?\s*class\s+\w+\s*{",
            method_pattern=r"(public|private|protected|static)?\s+[\w<>\[\]]+\s+\w+\s*\(.*?\)\s*{"
        )
    def split_js_ts_sections(self, code: str):
        """Extract JavaScript/TypeScript classes, functions, and methods."""
        return self.split_classes_and_methods(
            code,
            class_pattern=r"class\s+\w+\s*{",
            method_pattern=r"(function\s+\w+\s*\(.*?\)\s*{)|(const|let|var)\s+\w+\s*=\s*\(.*?\)\s*=>\s*{"
        )
    @staticmethod
    def split_classes_and_methods(code: str, class_pattern: str, method_pattern: str):
        """
        Extract both classes and their methods from the code.
        Returns a list of tuples: (section_text, section_type, start_line, end_line).
        """
        sections = []
        class_matches = list(re.finditer(class_pattern, code, re.MULTILINE))

        for class_match in class_matches:
            # Extract the full class block
            class_start = class_match.start()
            class_end = code.find("}", class_start) + 1  # Naive block detection
            class_text = code[class_start:class_end]
            class_start_line = code[:class_start].count("\n") + 1
            class_end_line = class_start_line + class_text.count("\n")

            # Add the class as a section
            sections.append((class_text, "class", class_start_line, class_end_line))

            # Extract methods within the class
            class_body = code[class_start:class_end]
            method_matches = re.finditer(method_pattern, class_body, re.MULTILINE)
            for method_match in method_matches:
                method_start = class_start + method_match.start()
                method_end = code.find("}", method_start) + 1
                method_text = code[method_start:method_end]
                method_start_line = code[:method_start].count("\n") + 1
                method_end_line = method_start_line + method_text.count("\n")

                sections.append((method_text, "class function", method_start_line, method_end_line))

        # Extract standalone methods (functions outside classes)
        standalone_methods = re.finditer(method_pattern, code, re.MULTILINE)
        for method_match in standalone_methods:
            if not any(class_start <= method_match.start() <= class_end for class_text, _, class_start, class_end in sections if _ == "class"):
                method_start = method_match.start()
                method_end = code.find("}", method_start) + 1
                method_text = code[method_start:method_end]
                method_start_line = code[:method_start].count("\n") + 1
                method_end_line = method_start_line + method_text.count("\n")

                sections.append((method_text, "function", method_start_line, method_end_line))

        return sections

DATA_CLEANER = lambda text: TextProcessor.clean_text_for_openai_embedding(text)
PRETRAIN = lambda text: {"text": DATA_CLEANER(text)}
FINETUNE = lambda system, user, assistant: {
    "messages": [
        {"role": "system", "content": DATA_CLEANER(system)},
        {"role": "user", "content": DATA_CLEANER(user)},
        {"role": "assistant", "content": DATA_CLEANER(assistant)},
    ]
}

@RaiRegistry.register("processor", name="format")
class FormatProcessor:

    @staticmethod
    def TO_PRETRAIN(text):
        return {"text": DATA_CLEANER(text)}
    @staticmethod
    def TO_FINETUNE(system, user, assistant):
        return {
            "messages": [
                {"role": "system", "content": DATA_CLEANER(system)},
                {"role": "user", "content": DATA_CLEANER(user)},
                {"role": "assistant", "content": DATA_CLEANER(assistant)},
            ]
        }

@RaiRegistry.register("processor", name="text")
class TextProcessor(DictComparator, StringComparator):
    unicode_replacements = {
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
    title_pattern = re.compile(r'\b(' + '|'.join([
        'Mr\.', 'Mrs\.', 'Miss\.', 'Ms\.', 'Dr\.', 'Prof\.', 'Capt\.', 'Col\.', 'Gen\.', 'Lt\.', 'Maj\.', 'Sgt\.',
        'Adm\.', 'Cpl\.', 'Rev\.', 'Sen\.', 'Rep\.', 'Gov\.', 'Pres\.', 'Rt\.', 'Hon\.', 'Cmdr\.', 'Amb\.', 'Sec\.',
        'Dir\.',  # Add any additional titles as necessary
    ]) + r')\b')
    text_splitter_web = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=1000,
        add_start_index=True,
    )
    text_splitter_pdf = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    text_splitter_table = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=0,
        add_start_index=True,
    )

    content_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=2500,
        add_start_index=True,
    )


    def split_web_docs(self, docs: []): return self.text_splitter_web.split_documents(docs)
    def split_pdf_docs(self, docs: []): return self.text_splitter_pdf.split_documents(docs)
    def split_table_docs(self, docs: []): return self.text_splitter_table.split_documents(docs)

    @staticmethod
    def TEXT_CLEANER(text): return TextProcessor.clean_text_for_openai_embedding(text)
    @staticmethod
    def NORMALIZE_NEW_LINES(text: str) -> str:
        if text is None: return ""
        cleaned_text = text.replace("\r", "\n")
        cleaned_text = re.sub(r'\s\s+', '\n', cleaned_text).strip()
        cleaned_text = re.sub(r'\n+', '\n', cleaned_text).strip()
        return cleaned_text

    @staticmethod
    def NORMALIZER(text: str) -> str:
        if text is None: return ""
        try:
            text = unicodedata.normalize('NFC', text)
        except Exception as e:
            Log.w(f"Unicode normalization failed: {e}")
        try:
            text = ''.join(char for char in text if
                                   char.isprintable() and not unicodedata.category(char).startswith('C'))
        except Exception as e:
            Log.w(f"Removing non-printable characters failed: {e}")
        text = re.sub(r'[\U00010000-\U0010FFFF]+', '', text)
        text = re.sub(r'\n+', '\n', text).strip()
        return text

    @staticmethod
    def ensure_within_limit(text: str, limit: int) -> str:
        """
        Ensures that the provided text is within the specified character limit.
        If text exceeds the limit, it will be truncated to exactly match the limit.

        Args:
            text (str): The input string to check and potentially truncate.
            limit (int): The maximum allowed length of the string.

        Returns:
            str: Original text if within the limit; otherwise, truncated text.
        """
        try:
            if limit < 0: return text
            return text if len(text) <= limit else text[:limit]
        except Exception as e:
            print(e)
            return text

    @staticmethod
    def NORMALIZE_SPACES(text: str) -> str:
        cleaned_text = re.sub(r'\s\s+', ' ', text).strip()
        return cleaned_text

    @staticmethod
    def content_is_valid(content: str) -> bool:
        try:
            return len(TextProcessor.TEXT_CLEANER(content)) > 5
        except Exception as e:
            print(e)
            return False

    """ MASTER """
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
                Log.w("Converting Input to String.")
                text = str(text)
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
    def split_text_to_sentences(text, toString: bool = False):
        # Split text into sentences for embedding
        cleaned_sentences = to_sentences(content=text, combineQuotes=True)
        if toString: return str(cleaned_sentences)
        else: return cleaned_sentences
    @staticmethod
    def split_text_to_paragraphs(text):
        # Split the text by two or more newlines
        paragraphs = re.split(r'\n+', text.strip())
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
    @staticmethod
    def split_string_by_limit(input_string, char_limit:int=1500):
        words = input_string.split()
        result = []
        current_string = ""

        for word in words:
            # Check if adding the next word would exceed the character limit
            if len(current_string) + len(word) + 1 <= char_limit:
                # If not, add the word to the current string
                if current_string:
                    current_string += " " + word
                else:
                    current_string = word
            else:
                # If it would exceed the limit, append the current string to result
                result.append(current_string)
                # Start a new string with the current word
                current_string = word

        # Append the last string if it exists
        if current_string:
            result.append(current_string)

        return result
    @staticmethod
    def format_dataset_to_string(dataset) -> str:
        temp = ""
        if type(dataset) in [list, tuple]:
            temp = "DATASET:\n"
            for item in dataset:
                temp = f"{temp}\n{item}"
        elif type(dataset) in [str]:
            temp = dataset
        elif type(dataset) in [dict]:
            temp = "DATASET:\n"
            for key, value in dataset.items():
                temp = f"{temp}\n{key}: {value}"
        return temp

    @staticmethod
    def is_within_model_token_limit(text: str, model: str = "gpt-4o", max_tokens: int = 8192) -> bool:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to a default encoding if model name not found
            encoding = tiktoken.get_encoding("gpt2")

        # Encode the text to tokens
        tokenized_text = encoding.encode(text)
        token_count = len(tokenized_text)

        return token_count <= max_tokens
    @staticmethod
    def string_length_is_within(text: str, max_length: int = 100):
        if len(text) > max_length: return False
        else: return True

FORM_SENTENCE = lambda strContent, startIndex, endIndex, caboose: f"{strContent[startIndex:endIndex]}{caboose}"

"""Move to Engines"""
def to_sentences(content: str, combineQuotes=True):
    """100%! WORKING!!!"""
    content = __prepare_content_for_sentence_extraction(content)
    current_index, start_index, quotation_count, sentences = 0, 0, 0, []
    # -> Loop every character in content (str).
    for currentChar in content:
        # -> Verify we have next (+3) characters.
        if current_index >= len(content) - 3:
            if MATH.is_even_number(quotation_count + 1):
                sent = content[start_index:-1] + currentChar + '"'
            else:
                sent = content[start_index:-1] + currentChar
            sentences.append(sent)
            break
        plusOneChar = content[current_index + 1]
        # -> Keep count of quotations. Even = Closed and Odd = Open
        if is_quotation(currentChar):
            quotation_count += 1
        # -> Verify current (0) character is a "sentence ending character" EX: . ! ?
        if __is_sentence_ender(currentChar):
            # -> Verify next (+1) character is a space or quote "
            if is_space(plusOneChar) or is_quotation(plusOneChar):
                QM = False
                # -> Verify next (+1) character is a quotation and are we "Quote Closed"
                if is_quotation(plusOneChar) and MATH.is_even_number(quotation_count + 1):
                    QM = True
                plusTwoChar = str(content[current_index + 2])
                plusThreeChar = str(content[current_index + 3])
                # -> Verify that +2 character is a valid "Sentence Beginner"
                if __is_sentence_beginner(plusTwoChar if not QM else plusThreeChar):
                    # -> Verify next character is a space
                    if is_space(plusOneChar if not QM else plusTwoChar):
                        minusOneChar = str(content[current_index - 1])
                        minusTwoChar = str(content[current_index - 2])
                        minuxThreeChar = str(content[current_index - 3])
                        # -> Verify previous three characters do not include a period
                        if not are_periods(minusOneChar, minusTwoChar, minuxThreeChar):
                            if combineQuotes and not MATH.is_even_number(quotation_count if not QM else quotation_count + 1):
                                current_index += 1
                                continue
                            # -> VERIFIED! Create sentence.
                            sent = FORM_SENTENCE(content, start_index, current_index, currentChar if not QM else f'{currentChar}"')
                            start_index = current_index + 2
                            sentences.append(sent)
        current_index += 1
    return sentences

# SENTENCE_ENDERS = ['.', '?', '!']
def __prepare_content_for_sentence_extraction(content):
    return content.strip().replace("\n", " ").replace("  ", " ")

def __is_sentence_ender(content):
    if str(content) in SENTENCE_ENDERS:
        return True
    return False
def __is_sentence_beginner(content):
    if is_in_alphabet(content):
        return True
    elif is_quotation(content):
        return True
    elif is_single_number(content):
        return True
    return False
def is_in_alphabet_lower(content:str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar in ALPHABET_LOWER:
        return True
    return False
def is_in_alphabet_upper(content:str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar in ALPHABET_UPPER:
        return True
    return False
def is_in_alphabet(content:str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar in ALPHABET_ALL:
        return True
    return False
def is_single_number(content):
    if type(content) != int:
        content = LIST.get(0, content, default=False)
    if content in NUMBERS_SINGLE:
        return True
    return False
def is_capital(content: str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar and str(firstChar).isupper():
        return True
    return False
def are_capital(*content: str):
    for item in content:
        if not is_capital(item):
            return False
    return True
def are_periods(*content: str):
    for item in content:
        if not is_period(item):
            return False
    return True
def is_period(content:str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar and str(content) == ".":
        return True
    return False
def are_periods_or_capitals(*content:str):
    for item in content:
        if is_capital(item) or is_period(item):
            return True
    return False
def is_empty(content: str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar and not content or content == ' ' or content == '' or str(content) == " ":
        return True
    return False
def are_empty(*content: str):
    for item in content:
        if not item or item == ' ' or item == '' or str(item) == " ":
            return True
    return False
def is_quotation(content:str):
    encoded_character = str(content).encode('utf-8')
    if content == '"':
        return True
    elif encoded_character in QUOTES_ENCODINGS:
        return True
    return False
def is_space(content:str):
    firstChar = LIST.get(0, content, default=False)
    if firstChar and str(content) == ' ':
        return True
    return False
def is_space_or_quotation(content):
    if is_quotation(content) or is_space(content):
        return True
    return False
