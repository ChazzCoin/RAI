
import re
import uuid

from tqdm import tqdm

from rai.assistant.openai_client import generate_embeddings


class DocPreparer:
    @staticmethod
    def prepare_chroma_documents(texts: [str], metadata: dict):
        items = []
        for idx, txt in enumerate(tqdm(texts, desc="Preparing Documents for chromadb...", colour="yellow")):
            temp = {
                "id": f"{str(uuid.uuid4())}:{str(idx)}",
                "text": txt,
                "vector": generate_embeddings(text=txt),
                "metadata": metadata,
            }
            items.append(temp)
        return items

    @staticmethod
    def ensure_string_for_chroma(dic: {}, default={}):
        final_meta = {}
        try:
            for key, value in dic.items():
                final_meta[str(key)] = str(value)
            return final_meta
        except Exception as e:
            print(e)
            return default

    @staticmethod
    def get_texts(docs: []):
        metadatas = [doc.page_content for doc in docs]
        return metadatas
    @staticmethod
    def get_metadatas(docs: []):
        metadatas = [{**doc.metadata, **({})} for doc in docs]
        return metadatas


def remove_excess_newlines(text: str) -> str:
    """
    Replace two or more consecutive newline characters with a single newline.

    :param text: The input string to process.
    :return: The modified string with consecutive newlines reduced to one.
    """
    return re.sub(r'\n{2,}', '\n', text)


def remove_js_css_and_html_tags(text: str) -> str:
    """
    Removes <script>...</script> (JS code), <style>...</style> (CSS code),
    all remaining HTML tags, and standalone CSS blocks (e.g., something { ... }).

    :param text: A string potentially containing HTML, JS, or CSS code.
    :return: A cleaned string containing only textual content.
    """
    # 1. Remove any <script>...</script> blocks (including multiline)
    text_no_scripts = re.sub(
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 2. Remove any <style>...</style> blocks (including multiline)
    text_no_scripts_no_styles = re.sub(
        r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>',
        '',
        text_no_scripts,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 3. Remove all remaining HTML tags
    text_no_html_tags = re.sub(r'<[^>]+>', '', text_no_scripts_no_styles)

    # 4. Remove standalone CSS blocks: anything like "selector { ... }"
    #    This captures lines of the form:
    #       .className { color: red; }
    #       h1, h2 { margin: 0; }
    #       #id { background: blue; }
    #       *#dm *.dmBody div.u_1158193019 { ... }
    #    If you need more advanced handling (like nested braces), you'll want a parser,
    #    but this should handle most basic CSS usage.
    text_no_css_blocks = re.sub(
        r'(?:[^\{\}]+\{[^{}]*\})',
        '',
        text_no_html_tags,
        flags=re.MULTILINE | re.DOTALL
    )

    # 5. Clean up extra whitespace and return
    return text_no_css_blocks.strip()

def ensure_string(data):
    """
    Recursively ensure that all values are strings.
    If a value is None, convert it to the literal string "null".
    """
    if data is None:
        return "null"
    elif isinstance(data, dict):
        # Convert keys and values to strings, with None replaced by "null"
        return {str(k): ensure_string(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Convert each list item to a string, replacing None with "null"
        return [ensure_string(item) for item in data]
    elif isinstance(data, (int, float, bool)):
        # Convert numbers/bools directly to strings
        return str(data)
    # For strings or anything else, just ensure it's a string
    return str(data)