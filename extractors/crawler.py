# import json
import tldextract
from urllib.parse import urljoin, urlparse
# import re
from extractors.extract_url import selenium_get_with_urls, selenium_get_with_urls_v2
from dataset.formatters.jsonlist import pipeline_convert_raw_text_to_jsonl_dataset
# from assistant import openai_client
# Set to hold crawled URLs
visited_urls = set()
# Dictionary to store scraped data
scraped_data = {}
# sp = """
# You are now my personal AI Training Assistant. I will provide you with raw datasets and you will do the following.
#
# 1. You will clean the dataset by removing any missing values, duplicates, and outliers.
# 2. You will read the data and you will come up with a list of questions that can be answered using the dataset.
# 3. You will reformat and return the list of questions/answers using the jsonl format to fine-tune using openai.
# 4. Only return the jsonl data for training.
# 5. System Prompt to use in training data: "You are a knowledgeable assistant for the Park City Soccer Club, providing information about soccer programs and club activities."
# Example Format:
# {"messages": [{"role": "system", "content": "You are a professional youth soccer mentor and advisor for parents of soccer players." }, {"role": "user", "content": "Question from the webpage contents?"}, {"role": "assistant", "content": "Answer to the question..."}]}
# """
def is_internal_url(url, base_url):
    # Ensure URL is within the same domain
    base_domain = tldextract.extract(base_url).domain
    url_domain = tldextract.extract(url).domain
    return base_domain == url_domain

def crawl_website(url, output_file='park_city_data.json'):
    if url in visited_urls:
        return
    base_domain = tldextract.extract(url).domain
    try:
        # Mark as visited
        visited_urls.add(url)
        # Fetch content
        results = selenium_get_with_urls_v2(url)
        page_text = results['page_content']
        urls = results['urls']
        scraped_data[url] = page_text

        """ Page Text to .txt file """

        print(f"Scraped {url}")
        pipeline_convert_raw_text_to_jsonl_dataset(page_text, output_file)
        # json_data = request_jsonl_formatting_from_ai(page_text)
        # save_jsonl_response(json_data, 'park_city_qa.jsonl')
        # Find and crawl internal links
        for link in urls:
            parsed_url = urlparse(link)
            # Normalize and ensure it's internal
            normalized_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            if is_internal_url(link, base_domain) and normalized_url not in visited_urls:
                crawl_website(normalized_url)
    except Exception as e:
        print(f"Failed to crawl {url}: {e}")

if __name__ == "__main__":
    crawl_website("https://www.parkcitysoccer.org/newpage", "../dataset/data/busa_qa.jsonl")
