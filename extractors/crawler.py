import tldextract
from urllib.parse import urljoin, urlparse
from files.FilePath import FilePath
from files.save import DataSaver
from dataset.DataTag import DataTag
from extractors.extract_url import selenium_get_with_urls, selenium_get_core_page_details
from F.LOG import Log
# Set to hold crawled URLs

Log = Log("WebCrawler")

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

visited_urls = set()
def crawl_website(url, page=0):
    if url in visited_urls:
        Log.i(f"{url} has already been visited, skipping...")
        return
    base_domain = tldextract.extract(url).domain
    out_directory = FilePath(FilePath.PENDING).add(base_domain)
    FilePath.ensure_directory_exists(out_directory.path())
    try:
        # Mark as visited
        visited_urls.add(url)
        # Fetch content
        results = selenium_get_core_page_details(url)
        page_text = results['content']
        urls = results['urls']
        details = results['details']
        title = base_domain
        if details['title']:
            title = details['title']
        scraped_data[url] = page_text

        page_text = DataTag.insert_tag(page_text, title, DataTag.TITLE)
        page_text = DataTag.insert_tag(page_text, url, DataTag.URL)
        """ Page Text to .txt file """
        DataSaver.save_txt(page_text, out_directory.temp_add(f"{title}-{page}.txt"))

        """ Convert to Training Data """
        # pipeline_convert_raw_text_to_jsonl_dataset(page_text, output_file)
        # json_data = request_jsonl_formatting_from_ai(page_text)
        # save_jsonl_response(json_data, 'park_city_qa.jsonl')
        # Find and crawl internal links
        for link in urls:
            parsed_url = urlparse(link)
            # Normalize and ensure it's internal
            normalized_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            if is_internal_url(link, base_domain) and normalized_url not in visited_urls:
                Log.i(f"Crawling new page: {normalized_url}:{page+1}")
                crawl_website(normalized_url, page=page + 1)
    except Exception as e:
        Log.e(f"Failed to crawl {url}: {e}")

if __name__ == "__main__":
    one = "https://www.barrowneuro.org"
    two = "https://www.mian-neurosurgery.com"
    crawl_website(two)
