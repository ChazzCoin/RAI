import re

from F import LIST

from nlp import Character
from nlp.Constants import STOP_WORDS

SEARCH_TERM = lambda searchTerm: fr'.*{str(searchTerm)}.*'
SEARCH_TERM_TWO = lambda searchTerm: fr'\b{searchTerm}\b'
REMOVE_SPECIAL_CHARACTERS = r'[^a-zA-Z0-9]'

CONTAINS_YEAR = r'\b[1-2][0-9][0-9][0-9]\b'
ONLY_CAPITAL_WORDS = r'([A-Z][a-z]+)'

EXTRACT_TICKERS_STRICT = r'[^\s$:(][A-Z]{1,5}(?=\s|\)|/|,|\.)'
EXTRACT_TICKERS_LIGHT = r'[^\s$:(][A-Za-z]{1,5}(?=\s|\)|/|,|\.)'

IS_URL = r'http.?://.*/'
FIND_URLS = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'


FINDALL = lambda regex, content: re.findall(regex, content)
SEARCH = lambda regex, content: re.search(regex, content)

def search(search_term, content):
    match = FINDALL(SEARCH_TERM(search_term), content)
    return match if len(match) >= 1 and match is not None else False

def contains(search_term, content):
    try:
        if type(content) in [list, tuple]:
            for itemContent in content:
                match = re.findall(fr'.*{str(search_term)}.*', itemContent)
                if len(match) >= 1 and match is not None:
                    return True
            return False
        else:
            match = re.findall(fr'.*{str(search_term)}.*', content)
            return True if len(match) >= 1 and match is not None else False
    except Exception as e:
        print(f"Failed to regex findall. {str(search_term)}, error=[ {e} ]")
        return False

def contains_strict(search_term, content):
    try:
        if type(content) in [list, tuple]:
            for itemContent in content:
                search_term = __remove_special_characters(search_term)
                match = re.findall(fr'\b{search_term}\b', itemContent)
                if len(match) >= 1 and match is not None:
                    return True
            return False
        else:
            search_term = __remove_special_characters(search_term)
            match = re.findall(fr'\b{search_term}\b', content)
            return True if len(match) >= 1 and match is not None else False
    except Exception as e:
        print(f"Failed to regex findall. {search_term}, error=[ {e} ]")
        return False

def contains_any(search_terms, content):
    search_terms = LIST.flatten(search_terms)
    for term in search_terms:
        temp = contains(term, content)
        if temp:
            return True
    return False

def locate_term_in_str(term, content):
    match = re.search(fr'\b{term}\b', content)
    if match:
        return match
    return False

def extract_only_capital_words_regex(content):
    capital_words = re.findall(r'([A-Z][a-z]+)', content)
    return capital_words

def extract_only_capital_words_manual(content):
    previous_char = " "
    current_index = 0
    start_index = 0
    start_enabled = False
    temp_words = []
    for char in content:
        if Character.is_capital(char) and Character.is_empty(char) and not start_enabled:
            start_index = current_index
            start_enabled = True
        if not Character.is_capital(char) and Character.is_empty(char) and start_enabled:
            end_index = current_index
            words = content[start_index:end_index-1]
            temp_words.append(words)
            start_enabled = False
        previous_char = char
        current_index += 1
    final_words = []
    for word in temp_words:
        if word.lower() in STOP_WORDS:
            continue
        final_words.append(word)
    return final_words


def __remove_special_characters(text):
    """ DEPRECATED """
    newText = re.sub('[^a-zA-Z0-9]', ' ', text)
    return newText