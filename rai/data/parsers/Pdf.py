from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def replace_t_with_space(list_of_documents):
    """
    Replaces all tab characters ('\t') with spaces in the page content of each document.

    Args:
        list_of_documents: A list of document objects, each with a 'page_content' attribute.

    Returns:
        The modified list of documents with tab characters replaced by spaces.
    """

    for doc in list_of_documents:
        doc.page_content = doc.page_content.replace('\t', ' ')  # Replace tabs with spaces
    return list_of_documents

def simple_pdf_to_documents(path, chunk_size=1000, chunk_overlap=200):
    # Load PDF documents
    loader = PyPDFLoader(path)
    documents = loader.load()

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    texts = text_splitter.split_documents(documents)
    cleaned_texts = replace_t_with_space(texts)
    return cleaned_texts




if __name__ == '__main__':
    path = "/Users/chazzromeo/Desktop/Proverbs-Unsorted/Chip generating electric power from quantum vacuum.pdf"
    data = simple_pdf_to_documents(path)
    if data:
        for item in data:
            print("\n----\n", item, "\n")
    # print(data)