from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

url = "https://www.parkcitysoccer.org/tournaments"
docs = [WebBaseLoader(url).load()]
docs_list = [item for sublist in docs for item in sublist]
# if docs:
#     for item in docs:
#         print(item)


# Split
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=500, chunk_overlap=0
)
doc_splits = text_splitter.split_documents(docs_list)
print(doc_splits)