"""
-> if CurrentCharacter is '.'
    - > if three previous characters are not periods
    - > if first next character is a space
    - > if second next character is a sentence beginner
"""
import re
from nlp import Character
from nlp import Re
from nlp import Cleaner as cleaner
from F import MATH, LIST
import string
MASTER_PREFIXES = [
        'Mr.', 'Mrs.', 'Miss.', 'Ms.', 'Dr.', 'Prof.', 'Capt.', 'Col.', 'Gen.', 'Lt.', 'Maj.', 'Sgt.',
        'Adm.', 'Cpl.', 'Rev.', 'Sen.', 'Rep.', 'Gov.', 'Pres.', 'Rt.', 'Hon.', 'Cmdr.', 'Amb.', 'Sec.',
        'Dir.', "Ltd.", "Fig.", "Fig .", "i.e.", "p.", "e.g." # Add any additional titles as necessary
    ]
FORM_SENTENCE = lambda strContent, startIndex, endIndex, caboose: f"{strContent[startIndex:endIndex]}{caboose}"
CLEAN_SENTENCE = lambda sentence: __clean_sentence(sentence)
def are_periods(characters: list) -> bool:
    """
    Check if each character in the input list is a period.

    Args:
        characters (list): The list of characters.

    Returns:
        list: A list of boolean values indicating if each character is a period.
    """
    results = [char == '.' for char in characters]
    for r in results:
        if r:
            return True
    return False

def has_title_prefix(text: str) -> bool:
    """
    Check if the input text contains any of the specified title prefixes.

    Args:
        text (str): The input text.

    Returns:
        bool: True if the text contains a title prefix, False otherwise.
    """
    prefixes = [
        'Mr.', 'Mrs.', 'Miss.', 'Ms.', 'Dr.', 'Prof.', 'Capt.', 'Col.', 'Gen.', 'Lt.', 'Maj.', 'Sgt.',
        'Adm.', 'Cpl.', 'Rev.', 'Sen.', 'Rep.', 'Gov.', 'Pres.', 'Rt.', 'Hon.', 'Cmdr.', 'Amb.', 'Sec.',
        'Dir.', "ed.", "Fig.", "Fig .", "i.e.", "p.", "e.g." # Add any additional titles as necessary
    ]
    if text in prefixes:
        return True
    return False
def clean_text_v2(text: str) -> str:
    """
    Clean the input text by removing special characters, non-alphabetic and non-numeric characters
    except periods and spaces, and any specific patterns.

    Args:
        text (str): The input text.

    Returns:
        str: The cleaned text.
    """
    # Step 1: Remove specific patterns (based on the provided training text)
    # This can include patterns like ©, ·dots·, bullets, etc.
    patterns_to_remove = [
        r'\[.*?\]',  # Remove content within brackets
        r'·',  # Remove dot indicators
        r'•',  # Remove bullet points
        r'\.\.\.\.',  # Remove four-point ellipsis
        r'\d{4}',  # Remove years
        r'\b[A-Za-z]+[0-9]+\b',  # Remove any alphanumeric words
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text)

    # Step 2: Remove all characters that are not alphabetic, numeric, period, or space
    text = re.sub(r'[^a-zA-Z0-9\s\.]', '', text)

    # Step 3: Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)

    # Step 4: Remove any extra whitespace from the beginning and end
    text = text.strip()

    return text

def __clean_sentence(sentence):
    """ All 'safe' in the case they don't need that particular cleaning job. """
    sentence = cleaner.lower_uppercase_A_characters(sentence)
    sentence = cleaner.replace_multi_spaces_with_one_spaces(sentence)
    sentence = cleaner.remove_space_before_sentence_ender(sentence)
    sentence = cleaner.replace_spaces_before_commas(sentence)
    sentence = cleaner.replace_spaces_before_rogue_s(sentence)
    sentence = __add_ending_period(sentence)
    sentence = __capitalize_first_letter(sentence)
    sentence = cleaner.remove_leading_number(sentence)
    sentence = cleaner.remove_spaces_from_beg_and_end(sentence)
    return sentence
def __capitalize_first_letter(text):
    return re.sub(r"^[a-z]", lambda x: x.group(0).upper(), text)
def __add_ending_period(content:str):
    last_char = content[-1]
    if Character.is_sentence_ender(last_char):
        return content
    return content + "."
def __prepare_content_for_sentence_extraction(content: str) -> str:
    content = cleaner.remove_COMMENT_X(content)
    content = cleaner.replace_multi_spaces_with_two_spaces(content)
    return str(content.strip()
            .replace("-  ", "")
            .replace("...", "")
            .replace("..", "")
            .replace(",", "")
            .replace("\n", " ")
            .replace("  ", " ")
            .replace("(", "")
            .replace(")", "")
            .replace(":", "")
            )

def to_sentences(content: str, combineQuotes=True):
    """ Master Sentence Extractor """
    content = clean_text_v2(content)
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
        plusTwoChar = str(content[current_index + 2])
        plusThreeChar = str(content[current_index + 3])
        # -> Keep count of quotations. Even = Closed and Odd = Open
        if Character.is_quotation(currentChar):
            quotation_count += 1
        # -> Verify current (0) character is a "sentence ending character" EX: . ! ?
        if Character.is_sentence_ender(currentChar):
            # -> Verify next (+1) character is a space or quote "
            if Character.is_space(plusOneChar) or Character.is_quotation(plusOneChar):
                QM = False
                # -> Verify next (+1) character is a quotation and are we "Quote Closed"
                if Character.is_quotation(plusOneChar) and MATH.is_even_number(quotation_count + 1):
                    QM = True
                # -> Verify that +2 character is a valid "Sentence Beginner"
                if Character.is_sentence_beginner(plusTwoChar if not QM else plusThreeChar):
                    # -> Verify next character is a space
                    if Character.is_space(plusOneChar if not QM else plusTwoChar):
                        minusOneChar = str(content[current_index - 1])
                        minusTwoChar = str(content[current_index - 2])
                        minuxThreeChar = str(content[current_index - 3])
                        fullFourChars = f'{minuxThreeChar}{minusTwoChar}{minusOneChar}{currentChar}'
                        fullThreeChars = f'{minusTwoChar}{minusOneChar}{currentChar}'
                        # hasPrefixFour = has_title_prefix(fullFourChars)
                        # hasPrefixThree = has_title_prefix(fullThreeChars)
                        hasPrefixFour = Re.contains_any(MASTER_PREFIXES, fullFourChars)
                        hasPrefixThree = Re.contains_any(MASTER_PREFIXES, fullThreeChars)
                        hasPeriods = are_periods([minusOneChar, minusTwoChar, minuxThreeChar])
                        # -> Verify previous three characters do not include a period
                        if not hasPeriods or not hasPrefixFour or not hasPrefixThree:
                            if combineQuotes and not MATH.is_even_number(quotation_count if not QM else quotation_count + 1):
                                current_index += 1
                                continue
                            # -> VERIFIED! Create sentence.
                            sent = FORM_SENTENCE(content, start_index, current_index, currentChar if not QM else f'{currentChar}"')
                            uncaught_sentences = __possible_uncaught_ending(sent)
                            if uncaught_sentences:
                                for uncaughtS in uncaught_sentences:
                                    if is_valid_sentence(uncaughtS):
                                        cleaned = CLEAN_SENTENCE(uncaughtS)
                                        sentences.append(cleaned)
                            else:
                                if is_valid_sentence(sent):
                                    cleaned = CLEAN_SENTENCE(sent)
                                    sentences.append(cleaned)
                            start_index = current_index + 2
        current_index += 1
    return sentences


def to_sentences_v2(content: str):
    """ Master Sentence Extractor """
    content = __prepare_content_for_sentence_extraction(content)
    current_index, start_index, quotation_count, sentences = 0, 0, 0, []
    # Loop every character in content (str).
    while current_index < len(content):
        currentChar = content[current_index]
        # Keep count of quotations. Even = Closed and Odd = Open
        if Character.is_quotation(currentChar):
            quotation_count += 1
        # Verify current character is a "sentence ending character" EX: . ! ?
        if Character.is_sentence_ender(currentChar):
            plusOneChar = content[current_index + 1] if current_index + 1 < len(content) else ''
            # Verify next (+1) character is a space or quote "
            if Character.is_space(plusOneChar) or Character.is_quotation(plusOneChar):
                QM = Character.is_quotation(plusOneChar) and MATH.is_even_number(quotation_count + 1)
                sentence_beginner_idx = current_index + (3 if QM else 2)
                if sentence_beginner_idx < len(content):
                    next_sentence_char = content[sentence_beginner_idx]
                    # Verify that next character is a valid "Sentence Beginner"
                    if Character.is_sentence_beginner(next_sentence_char):
                        # VERIFIED! Create sentence.
                        sent = FORM_SENTENCE(content, start_index, current_index,
                                             currentChar if not QM else f'{currentChar}"')
                        if is_valid_sentence(sent):
                            cleaned = CLEAN_SENTENCE(sent)
                            sentences.append(cleaned)
                        start_index = current_index + 2
        current_index += 1

    if start_index < len(content):
        last_sentence = content[start_index:].strip()
        if is_valid_sentence(last_sentence):
            sentences.append(CLEAN_SENTENCE(last_sentence))

    return sentences



def handle_abbreviations_and_titles(content):
    patterns = [
        (r'(?<!Mr|Ms|Dr|Prof|Inc|Ltd|Jr|Sr|Mx)\.(?=\s*[A-Z])', '||PERIOD||'),  # Preserve periods acting as sentence ends
        (r'(\b\d+\.\d+|\b[A-Z]\.)', lambda m: m.group(1).replace('.', '¶¶PERIOD¶¶'))  # Preserve periods within numbers/abbreviations
    ]
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    content = content.replace('||PERIOD||', '.').replace('¶¶PERIOD¶¶', '.')
    return content

def is_suitable(sentence):
    sentence = sentence.strip()
    # Ensure sentence has more than two words
    if len(sentence.split()) <= 45:
        return False

    # Check if it starts with an uppercase letter and ends with appropriate punctuation
    if not re.match(r'^[A-Z][^.!?]*[.!?]$', sentence):
        return False

    # Filter out nonsensical or placeholder content
    nonsensical_patterns = [r'\bLorem ipsum\b', r'\bDolor sit\b']
    for pattern in nonsensical_patterns:
        if re.search(pattern, sentence, re.IGNORECASE):
            return False

    # Filter out metadata or likely references
    metadata_patterns = [r'\b\d{4}\b', r'\bUS\b', r'\bNo\.:', r'\bPatent\b', r'\bPublication\b', r'\bDate\b', r'\bFig\b']
    for pattern in metadata_patterns:
        if re.search(pattern, sentence):
            return False

    return True
def filter_sentences_for_ai_training(sentences):
    """ Filter sentences to retain only those suitable for AI training """
    return [sentence for sentence in sentences if is_suitable(sentence)]


def to_sentences_v3(content: str):
    """ Master Sentence Extractor with refined logic """
    content = __prepare_content_for_sentence_extraction(content)
    content = handle_abbreviations_and_titles(content)

    current_index, start_index, quotation_count, sentences = 0, 0, 0, []

    while current_index < len(content):
        currentChar = content[current_index]

        if Character.is_quotation(currentChar):
            quotation_count += 1

        if Character.is_sentence_ender(currentChar):
            plusOneChar = content[current_index + 1] if current_index + 1 < len(content) else ''
            if Character.is_space(plusOneChar) or Character.is_quotation(plusOneChar):
                QM = Character.is_quotation(plusOneChar) and MATH.is_even_number(quotation_count + 1)
                sentence_beginner_idx = current_index + (3 if QM else 2)

                if sentence_beginner_idx < len(content):
                    next_sentence_char = content[sentence_beginner_idx]

                    if Character.is_sentence_beginner(next_sentence_char):
                        sent = FORM_SENTENCE(content, start_index, current_index,
                                             currentChar if not QM else f'{currentChar}"')
                        if is_valid_sentence(sent):
                            cleaned = CLEAN_SENTENCE(sent)
                            sentences.append(cleaned)
                        start_index = current_index + 2
        current_index += 1

    if start_index < len(content):
        last_sentence = content[start_index:].strip()
        if is_valid_sentence(last_sentence):
            sentences.append(CLEAN_SENTENCE(last_sentence))

    return sentences


def merge_into_body(sentences:[]):
    body = ""
    for sentence in sentences:
        body += sentence + " "
    return str(body).strip()
def is_valid_sentence(sentence: str) -> bool:
    if not sentence:
        return False
    if sentence[0].islower() or sentence[-1] not in string.punctuation:
        return False
    # if sentence contains no spaces.
    if not has_spaces(sentence):
        return False
    # if sentence only contains 1 word.
    if not has_two_words(sentence):
        return False
    return True
def has_spaces(content:str):
    return bool(re.search(r"\s", content))
def has_two_words(content:str):
    if len(content) <= 2:
        return False
    for index in range(len(content)):
        if index >= len(content) - 2:
            break
        char = content[index]
        char_plus_one = content[index+1]
        char_plus_two = content[index+2]
        if Character.is_in_alphabet(char):
            first_char = True
        else:
            first_char = False
        if Character.is_space(char_plus_one):
            space = True
        else:
            space = False
        if Character.is_in_alphabet(char_plus_two):
            second_char = True
        else:
            second_char = False
        if first_char and space and second_char:
            return True
    return False
def __possible_uncaught_ending(content:str):
    if len(content) <= 3:
        return False
    for index in range(len(content)):
        if index >= len(content) - 3:
            break
        char = content[index]
        char_plus_one = content[index+1]
        char_plus_two = content[index+2]
        char_plus_three = content[index+3]
        if Character.is_in_alphabet_lower(char) or Character.is_sentence_ender(char):
            first_char = True
        else:
            first_char = False
        if Character.is_space(char_plus_one) and Character.is_space(char_plus_two):
            space = True
        else:
            space = False
        if Character.is_in_alphabet_upper(char_plus_three):
            second_char = True
        else:
            second_char = False
        if first_char and space and second_char:
            sent_one = content[:index+1].strip()
            if not Character.is_sentence_ender(sent_one[-1]):
                sent_one = __add_ending_period(sent_one)
            sent_two = content[index+2:].strip()
            againOne = __possible_uncaught_ending(sent_one)
            againTwo = __possible_uncaught_ending(sent_two)
            if againOne:
                sent_one = againOne
            if againTwo:
                sent_two = againTwo
            return LIST.flatten([sent_one, sent_two])
    return None

