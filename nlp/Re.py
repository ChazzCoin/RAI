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


def extract_hashtags(text: str) -> list:
    """
    Extracts hashtags from the text.

    A hashtag is defined as a '#' followed immediately by alphanumeric characters or underscores.
    For example: #DesignTrends, #2025Innovation.

    Args:
        text (str): The input text containing hashtags.

    Returns:
        list: A list of hashtags found in the text.
    """
    hashtag_regex = re.compile(r'(?<!\w)#\w+')
    return hashtag_regex.findall(text)


def extract_mentions(text: str) -> list:
    """
    Extracts mentions (e.g., social media handles) from the text.

    A mention is defined as an '@' followed by alphanumeric characters or underscores.
    For example: @user, @example_handle.

    Args:
        text (str): The input text containing mentions.

    Returns:
        list: A list of mentions found in the text.
    """
    mention_regex = re.compile(r'(?<!\w)@\w+')
    return mention_regex.findall(text)


def extract_currency_amounts(text: str) -> list:
    """
    Extracts currency amounts from the text.

    Supports common currency symbols ($, €, £, ¥) preceding numbers formatted with optional commas
    and decimals, as well as currency codes (USD, EUR, GBP, JPY) optionally preceding the amount.

    Examples:
      - "$1,299.99"
      - "USD 999.99"
      - "€3,450.75"

    Args:
        text (str): The input text containing currency amounts.

    Returns:
        list: A list of currency amounts found in the text.
    """
    currency_regex = re.compile(
        r'(?<!\w)(?:'
        r'(?:[\$€£¥]\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?\b)'
        r'|'
        r'(?:\b(?:USD|EUR|GBP|JPY)\s?(?:[\$€£¥])?\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?\b)'
        r')'
    )
    return currency_regex.findall(text)


def extract_ipv6_addresses(text: str) -> list:
    """
    Extracts IPv6 addresses from the text.

    The regex attempts to capture many valid IPv6 formats, including full, abbreviated,
    and shorthand notations.

    Examples:
      - "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
      - "::1"
      - "fe80::1ff:fe23:4567:890a"

    Args:
        text (str): The input text containing IPv6 addresses.

    Returns:
        list: A list of IPv6 addresses found in the text.
    """
    ipv6_regex = re.compile(r'''
\b(
    (?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4} |             # 1:2:3:4:5:6:7:8
    (?:[A-F0-9]{1,4}:){1,7}: |                         # 1::                              1:2:3:4:5:6:7::
    (?:[A-F0-9]{1,4}:){1,6}:[A-F0-9]{1,4} |             # 1::8             1:2:3:4:5:6::8
    (?:[A-F0-9]{1,4}:){1,5}(?::[A-F0-9]{1,4}){1,2} |    # 1::7:8           1:2:3:4:5::7:8
    (?:[A-F0-9]{1,4}:){1,4}(?::[A-F0-9]{1,4}){1,3} |    # 1::6:7:8         1:2:3:4::6:7:8
    (?:[A-F0-9]{1,4}:){1,3}(?::[A-F0-9]{1,4}){1,4} |    # 1::5:6:7:8       1:2:3::5:6:7:8
    (?:[A-F0-9]{1,4}:){1,2}(?::[A-F0-9]{1,4}){1,5} |    # 1::4:5:6:7:8     1:2::4:5:6:7:8
    [A-F0-9]{1,4}:(?:(?::[A-F0-9]{1,4}){1,6}) |         # 1::3:4:5:6:7:8   1::4:5:6:7:8
    :(?:(?::[A-F0-9]{1,4}){1,7}|:)                     # ::2:3:4:5:6:7:8  ::8  ::
)
\b
''', re.VERBOSE | re.IGNORECASE)
    return ipv6_regex.findall(text)


def extract_times(text: str) -> list:
    """
    Extracts time expressions from the text.

    Supports:
      - 24-hour formats (e.g., "09:30", "23:59:59")
      - 12-hour formats with optional AM/PM (e.g., "09:30 AM", "3:15pm")

    Args:
        text (str): The input text containing time expressions.

    Returns:
        list: A list of time strings found in the text.
    """
    time_regex = re.compile(
        r'\b((?:[01]?\d|2[0-3])(?::[0-5]\d){1,2}(?:\s?[APMapm]{2})?)\b'
    )
    return time_regex.findall(text)


def extract_percentages(text: str) -> list:
    """
    Extracts percentage expressions from the text.

    Matches whole numbers or decimals followed immediately by a percent sign.

    Examples:
      - "99.5%"
      - "50%"

    Args:
        text (str): The input text containing percentages.

    Returns:
        list: A list of percentage strings found in the text.
    """
    percentage_regex = re.compile(r'\b\d+(?:\.\d+)?%\b')
    return percentage_regex.findall(text)


def extract_hex_colors(text: str) -> list:
    """
    Extracts hexadecimal color codes from the text.

    Matches color codes in the form of 3 or 6 hexadecimal digits preceded by a '#' symbol.

    Examples:
      - "#fff"
      - "#123ABC"

    Args:
        text (str): The input text containing hex color codes.

    Returns:
        list: A list of hex color codes found in the text.
    """
    hex_color_regex = re.compile(r'\B#(?:[0-9a-fA-F]{3}){1,2}\b')
    return hex_color_regex.findall(text)
def extract_phone_numbers(text: str) -> list:
    """
    Extracts phone numbers from the provided text using a robust regex.

    Supports various common phone number formats including:
      - (123) 456-7890
      - 123-456-7890
      - 123.456.7890
      - 1234567890
      - +1 (123) 456-7890 ext 101

    Args:
        text (str): The input text containing phone numbers.

    Returns:
        list: A list of formatted phone numbers extracted from the text.
    """
    phone_regex = re.compile(
        r"""(?x)                            # Enable verbose mode
        (?:
          (?:\+?(\d{1,3}))?                 # Optional country code
          [\s\-.]*                         # Optional separators
        )?
        (?:\(?(\d{3})\)?                    # Area code with or without parentheses
        [\s\-.]*)                          # Optional separator
        (\d{3})                            # First 3 digits
        [\s\-.]*                           # Optional separator
        (\d{4})                            # Last 4 digits
        (?:[\s]*(?:#|x\.?|ext\.?)[\s]*(\d+))? # Optional extension
        """)

    matches = phone_regex.findall(text)
    phone_numbers = []
    for match in matches:
        country, area, first, last, ext = match
        phone = ""
        if country:
            phone += f"+{country} "
        phone += f"({area}) {first}-{last}"
        if ext:
            phone += f" ext {ext}"
        phone_numbers.append(phone)
    return phone_numbers
def extract_emails(text: str) -> list:
    """
    Extracts email addresses from the provided text using a robust regex.

    The regex matches email addresses that consist of alphanumeric characters,
    dots, underscores, percent signs, plus or minus signs before the '@',
    and a valid domain name after.

    Args:
        text (str): The input text containing email addresses.

    Returns:
        list: A list of email addresses found in the text.
    """
    email_regex = re.compile(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    )
    return email_regex.findall(text)
def extract_addresses(text: str) -> list:
    """
    Extracts potential U.S.-style physical addresses from the provided text.

    This regex is designed to capture common U.S. address formats that include:
      - A street number (1-5 digits)
      - A street name composed of one or more words (letters, numbers, dots, or hyphens)
      - A street type (e.g., Street, St, Road, Rd, Avenue, Ave, Boulevard, Blvd, etc.)
      - Optionally, a city (after a comma)
      - Optionally, a state (2 uppercase letters after a comma)
      - Optionally, a ZIP code (5 digits with an optional 4-digit extension)

    Note:
      - Addresses vary greatly in structure, and this regex may not capture every valid case.
      - Adjustments may be needed for international addresses or non-standard formats.

    Args:
        text (str): The input string that may contain one or more addresses.

    Returns:
        list: A list of matched address strings.
    """
    address_regex = re.compile(r'''
        (                                   # Start of the address match
          \d{1,5}\s+                       # Street number (1 to 5 digits) followed by whitespace
          (?:[A-Za-z0-9\.\-]+\s+)+           # One or more words for the street name
          (?:Street|St|Road|Rd|Avenue|Ave|
             Boulevard|Blvd|Lane|Ln|Drive|Dr|
             Court|Ct|Plaza|Plz|Square|Sq|Loop|Way)  # Street type
          (?:,\s*[A-Za-z\.\s]+)?             # Optional city preceded by a comma
          (?:,\s*[A-Z]{2})?                 # Optional state (2 uppercase letters) preceded by a comma
          (?:\s+\d{5}(?:-\d{4})?)?           # Optional ZIP code (5 digits with optional -4 digits)
        ) 
        ''', re.VERBOSE)

    # Find all non-overlapping matches of the address pattern
    matches = address_regex.findall(text)

    # Clean up any extraneous whitespace from each match and return
    return [match.strip() for match in matches if match.strip()]


def extract_urls(text: str) -> list:
    """
    Extracts all valid URLs from the provided text using a robust regular expression.

    Args:
        text (str): The input string potentially containing URLs.

    Returns:
        list: A list of all URLs found in the input text.
    """
    # This regex pattern is designed to match HTTP, HTTPS, and FTP URLs,
    # and includes advanced IP address and domain matching rules.
    url_regex = re.compile(
        r"("  # begin capture group for the full URL
        r"(?:(?:https?|ftp):\/\/)"  # protocol
        r"(?:\S+(?::\S*)?@)?"  # optional authentication
        r"(?:"
        # IP address exclusion (private & local networks)
        r"(?!(?:10|127)(?:\.\d{1,3}){3})"
        r"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})"
        r"(?!(?:172\.(?:1[6-9]|2\d|3[0-1]))(?:\.\d{1,3}){2})"
        # IP address dotted notation octets
        r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
        r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
        r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-5]))"
        r"|"  # OR domain name
        r"(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)"
        r"(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*"
        r"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
        r")"
        r"(?::\d{2,5})?"  # optional port
        r"(?:\/\S*)?"  # optional path
        r")",
        re.IGNORECASE
    )

    # Use findall to return all non-overlapping matches of the regex pattern in the string
    return url_regex.findall(text)

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