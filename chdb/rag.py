import os
import uuid
from F import DATE, DICT
from assistant import openai_client as openai
from chdb.chroma import ChromaInstance
from dataset.TextCleaner import TextCleaner
from dataset import load_txt_file, load_json_file

class RAGWithChroma(ChromaInstance):

    """ Helper Insert Function """
    def add_raw_text(self, raw_text: str, title: str, topic: str = "general", url: str = ""):
        docs = self.prepare_raw_text(raw_text, title, topic, url)
        return self.add_documents(docs)

    """ Helper Insert Function """
    def add_web_page(self, page_text: str, title: str, topic: str = "webpage", url: str = ""):
        docs = self.prepare_raw_text(page_text, title, topic, url)
        return self.add_documents(docs)

    @staticmethod
    def prepare_raw_text(raw_text: str, doc_name: str, topic: str="general", url: str=""):
        prepped_documents = []
        try:
            paragraphs = TextCleaner.to_paragraphs_with_min_max(raw_text)
            page = 0
            for paragraph in paragraphs:
                id = f"{doc_name}:{str(page)}:{str(uuid.uuid4())}"
                prepped_documents.append({
                    'id': id,
                    'text': paragraph,
                    'metadata': {
                        'title': doc_name,
                        'date': DATE.get_now_month_day_year_str(),
                        'topic': topic,
                        'url': url
                    }
                })
                page += 1
            return prepped_documents
        except Exception as e:
            print(f"Error processing the text file: {e}")
            return prepped_documents

    def generate_answer(self, query: str, top_n: int = 3) -> str:
        """ 1. Form Prompts """
        q_results = self.query(query, n_results=top_n)
        system_prompt = self.inject_into_system_prompt(q_results)
        print(system_prompt, "\n------------\n")
        """ 2. Request AI Response """
        ai_response = openai.chat_request(system=system_prompt, user=query)
        """ 3. Form Final Chat Response """
        output = self.append_metadata_to_response(ai_response, q_results)
        """ 4. Print and Return Response """
        print("\nMODEL:\n", os.getenv("DEFAULT_OPENAI_MODEL"))
        print("\nQUESTION:\n", query)
        print("\nANSWER:\n", output)
        return output

    @staticmethod
    def parse_chromadb_results(results):
        # Extract the relevant data from the results dictionary
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        # distances = results.get('distances', [[]])[0]

        # Ensure all lists are of the same length
        if len(documents) == len(metadatas):
            for i in range(len(documents)):
                yield {
                    'document': documents[i],
                    'metadata': metadatas[i]
                }
        else:
            raise ValueError("The lengths of 'documents', 'metadatas', and 'distances' lists do not match.")

    @staticmethod
    def inject_into_system_prompt(user_message:str, specialty:str, docs, text:str=None) -> str:
        context = "" if text is None else text
        previous_title = ""
        previous_source = ""
        for doc in RAGWithChroma.parse_chromadb_results(docs):
            context += DICT.get('document', doc, '')
            metadata = DICT.get('metadata', doc, {})
            current_title = DICT.get('title', metadata, '')
            current_source = DICT.get('url', metadata, '')
            if current_title != previous_title:
                context += f"\nTitle: {previous_title}\nSource: {previous_source}\n"
            previous_title = current_title
            previous_source = current_source

        # Format the final prompt for OpenAI
        system_prompt = f"""
        Knowledge Base:
        {context}

        General Rules:
        1. Based on the knowledge base above, answer the following question(s) and also attach the source url for any information you return.
        2. If you do not know the answer, do not try to make something up, simply say you do not know.
        3. You will cite any sources you used at the bottom of the message for reference.
        4. Format the response in a human-friendly way to read and understand.
        
        User Rules:
        {specialty}
        
        User Prompt:
        {user_message}
        """
        return system_prompt

    @staticmethod
    def append_metadata_to_response(chat_response: str, metadata: list) -> str:
        # Prepare the sources section
        sources_info = "\n\nSources:\n"

        # Handle multiple or single documents
        if len(metadata) == 1:
            doc = metadata[0]
            sources_info += f"- {doc['title']} by {doc['url']}"
        else:
            for i, doc in enumerate(metadata, start=1):
                sources_info += f"{i}. {doc['title']} by {doc['url']}\n"

        # Append sources to the original chat response
        final_response = chat_response + sources_info
        return final_response

    def import_json(self, file_name, topic):
        js = load_json_file(file_name)
        # for url in js:
        #     page_contents = js[url]
        #     page_paras = to_paragraphs_with_min_max(page_contents)
        #     for para in page_paras:
        #         print(para)
        #         self.add_web_page(page_text=para, page_name=extract_page_extension(url), topic=topic, url=url)

    def import_txt(self, file_name):
        text = load_txt_file(file_name)
        self.add_raw_text(text, doc_name=file_name)

def extract_page_extension(url: str) -> str:
    from urllib.parse import urlparse
    # Parse the URL
    parsed_url = urlparse(url)
    # Split the path and get the last segment
    page_extension = parsed_url.path.strip('/').split('/')[-1]
    return page_extension

# Usage Example
if __name__ == "__main__":
    collect = "parkcitysc-new"
    rag_system = RAGWithChroma(collection_name=collect)
    # query = "Tell me about the futures program at park city soccer club..."
    # query = "What is the core philosophy of park citys competitive program?"
    query = "Joel person"
    # query = "What tournaments does the club host? What are their names?"
    # query = "How do I register my child for tryouts?"
    print(rag_system.get_all_documents(collection=collect))
    # print(rag_system.query(collection=collect, user_input=query))
    # all_docs = rag_system.query(user_input=query, debug=True)
    # answer = rag_system.generate_answer(query)