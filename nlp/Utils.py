from F import LIST, OS
import re

FILE_PATH_AND_NAME: str = __file__
FILE_PATH: str = OS.get_path(FILE_PATH_AND_NAME)

def get_source(sourceTerm):
    return OS.get_file_BY_searchTerm(sourceTerm, directoryPath=FILE_PATH)

def get_stop_words()-> list:
    return get_source('stopwords')

def remove_special_characters(text):
    """ DEPRECATED """
    newText = re.sub('[^a-zA-Z0-9]', ' ', str(text))
    return newText

def remove_empty_strings(list_of_strs: []):
    newS = []
    for word in list_of_strs:
        if word == '':
            continue
        newS.append(word)
    return newS

def replace(content, *args):
    for arg in args:
        content = content.replace(arg, " ")
    return content

def combine_args_str(*content: str) -> str:
    temp = ""
    content = LIST.flatten(content)
    for item in content:
        temp += " " + str(item)
    return str(temp).strip()


print(get_stop_words())