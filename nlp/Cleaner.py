import re

DATA_CLEANER = lambda raw_data: re.sub(r"[^a-zA-Z0-9.!,?\s']+|\n", " ", raw_data).replace("  ", " ")

def remove_all_special_characters(content:str, replaceWith=" "):
    return re.sub(r"[^a-zA-Z0-9.!,?\s']+|\n", replaceWith, content)

def remove_spaces_from_beg_and_end(content:str):
    return content.strip()

def lower_uppercase_A_characters(content:str):
    return re.sub(r"\sA\s", " a ", content)

def remove_COMMENT_X(content:str):
    return re.sub(r" COMMENT \d+ ", "", content)

def remove_double_spaces(content:str):
    return content.replace("  ", " ")

def remove_new_line_characters(content:str):
    return content.replace("\n", " ")

def remove_space_before_sentence_ender(content:str):
    return re.sub(r"([a-zA-Z])\s([.?!])", "", content)

def replace_multi_spaces_with_two_spaces(content:str):
    return re.sub(r"(?<=[^\s])\s{2,}(?=[^\s])", "  ", content)

def replace_multi_spaces_with_one_spaces(content:str):
    return re.sub(r"(?<=[^\s])\s{2,}(?=[^\s])", " ", content)

def replace_spaces_before_commas(content:str):
    return re.sub(r"(.)\s(,)", ",", content)

def replace_spaces_before_rogue_s(content:str):
    return re.sub(r"\s(s)\s", "s ", content)

def remove_leading_number(text: str) -> str:
    if text and str(text[0]).isdigit():
        return text[1:]
    return text