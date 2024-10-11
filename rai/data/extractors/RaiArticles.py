import base64
import os
import threading
import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from weasyprint import HTML
import logging
from rai.data.extractors._RaiWebDriver import WebDriver

def base_url_extractor(url):
    return urlparse(url).netloc

class RaiArticles:
    def __init__(self, base_url: str, output_dir: str = 'output'):
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.base = base_url_extractor(self.base_url)
        self.domain_name = urlparse(self.base_url).netloc.replace('.', '_')
        self.output_file = os.path.join(self.output_dir, f"{self.domain_name}.json")
        self.data_lock = threading.Lock()
        self._prepare_output_directory()
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _prepare_output_directory(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def _save_data(self, data: dict):
        with self.data_lock:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def _scrape_page(self, url: str):
        try:
            logging.info(f"Scraping URL: {url}")
            results = selenium_get_core_page_details_v2(url)
            text = results['content']
            details = results['details']
            main_image_url = results.get('main_image_url', None)
            cleaned_text = self._clean_text(text)

            if not cleaned_text:
                logging.warning("No content extracted from the page.")
                return

            data = {
                'url': url,
                'title': details.get('title', 'No Title'),
                'author': details.get('author', 'Unknown Author'),
                'date': details.get('date', 'Unknown Date'),
                'content': cleaned_text,
                'main_image_url': main_image_url
            }

            self._save_data(data)
            # Format the article data into an HTML/CSS document
            html_content = self._render_html(data)
            # Convert the HTML to a PDF file
            self._html_to_pdf(html_content)

        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")

    def start(self):
        self._scrape_page(self.base_url)
        logging.info("Scraping completed.")

    def _clean_text(self, text: str) -> str:
        text = ' '.join(text.split())
        return text

    def _render_html(self, article_data):
        # Define the HTML template with the requested design
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @font-face {{
                    font-family: 'OldEnglish';
                    src: url('file://{font_path}');
                }}
                body {{
                    font-family: 'Times New Roman', Times, serif;
                    margin: 50px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                h1.newspaper-name {{
                    font-family: 'OldEnglish', 'Times New Roman', Times, serif;
                    font-size: 72px;
                    text-align: center;
                    margin-bottom: 20px;
                }}
                h1.title {{
                    font-size: 36px;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 10px;
                }}
                p.author, p.date {{
                    font-size: 14px;
                    text-align: center;
                    font-style: italic;
                    margin: 0;
                }}
                hr {{
                    border: 0;
                    border-top: 1px solid #999;
                    margin: 20px 0;
                }}
                div.content {{
                    font-size: 16px;
                    line-height: 1.5;
                    text-align: justify;
                }}
                .dropcap:first-letter {{
                    float: left;
                    font-size: 60px;
                    line-height: 1;
                    padding-top: 5px;
                    padding-right: 8px;
                    padding-left: 3px;
                }}
                img.main-image {{
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1 class="newspaper-name">The Romeo Report</h1>
            {main_image_tag}
            <h1 class="title">{title}</h1>
            <p class="author">By {author}</p>
            <p class="date">{date}</p>
            <hr>
            <div class="content">
                {content_paragraphs}
            </div>
        </body>
        </html>
        """
        # Path to the Old English font file
        font_path = os.path.abspath('OldEnglish.ttf')

        # Ensure the font file exists
        if not os.path.isfile(font_path):
            logging.warning("Old English font file not found. Default font will be used.")
            font_path = ''

        # Handle the main image
        main_image_tag = ''
        if article_data.get('main_image_url'):
            image_url = article_data['main_image_url']
            # Download the image and encode it in base64
            image_data_uri = self._download_image_as_data_uri(image_url)
            if image_data_uri:
                main_image_tag = f'<img src="{image_data_uri}" class="main-image" alt="Main Image"/>'
            else:
                logging.warning("Failed to download main image.")
        else:
            logging.info("No main image found.")

        # Prepare the content paragraphs
        paragraphs = article_data['content'].split('\n\n')
        content_paragraphs = ''.join([
            f'<p class="{"dropcap" if i == 0 else ""}">{para}</p>'
            for i, para in enumerate(paragraphs) if para.strip()
        ])

        html_content = html_template.format(
            font_path=font_path,
            main_image_tag=main_image_tag,
            title=article_data['title'],
            author=article_data['author'],
            date=article_data['date'],
            content_paragraphs=content_paragraphs
        )
        return html_content

    def _download_image_as_data_uri(self, image_url):
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                mime_type = response.headers.get('Content-Type', 'image/jpeg')
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{image_base64}"
                logging.info("Image downloaded and converted to data URI.")
                return data_uri
            else:
                logging.error(f"Failed to download image. Status code: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error downloading image: {e}")
            return None

    def _html_to_pdf(self, html_content):
        pdf_filename = os.path.join(self.output_dir, f"{self.domain_name}.pdf")
        try:
            HTML(string=html_content, base_url=self.output_dir).write_pdf(pdf_filename)
            logging.info(f"PDF saved to {pdf_filename}")
        except Exception as e:
            logging.error(f"Error converting HTML to PDF: {e}")


def selenium_get_core_page_details_v2(url, wait_time=10, max_scrolls=3):
    webdrive = WebDriver()
    core_details = {
        'title': '',
        'author': '',
        'date': ''
    }
    try:
        logging.info(f"Opening URL: {url}")
        webdrive.open(url)
        driver = webdrive.driver

        core_details['title'] = driver.title

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Extract title, author, date
        title_tag = soup.find('title')
        if title_tag:
            core_details['title'] = title_tag.get_text(strip=True)
        # Extract author
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta and author_meta.get('content'):
            core_details['author'] = author_meta['content']
        else:
            author_tag = soup.find(class_='author')
            if author_tag:
                core_details['author'] = author_tag.get_text(strip=True)

        # Extract date
        date_meta = soup.find('meta', {'name': 'date'})
        if date_meta and date_meta.get('content'):
            core_details['date'] = date_meta['content']
        else:
            date_tag = soup.find(class_='date')
            if date_tag:
                core_details['date'] = date_tag.get_text(strip=True)

        page_content = extract_full_content(soup)
        if page_content:
            logging.info("Successfully extracted page content.")
        else:
            logging.warning("No content extracted from the page.")

        main_image_url = extract_main_image(soup)
        if main_image_url:
            logging.info(f"Main image URL found: {main_image_url}")
        else:
            logging.info("No main image URL found.")

        page_content = extract_full_content(soup)
        if page_content:
            logging.info("Successfully extracted page content.")
        else:
            logging.warning("No content extracted from the page.")

        return {
            "details": core_details,
            "content": page_content,
            "main_image_url": main_image_url
        }
    except Exception as e:
        logging.error(f"Error in selenium_get_core_page_details_v2: {e}")
        return {
            "details": core_details,
            "content": '',
            "main_image_url": None
        }
    finally:
        logging.info("Closing WebDriver.")
        webdrive.quit()

def extract_main_image(soup):
    # Try to find the main image from meta tags
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return og_image['content']

    twitter_image = soup.find('meta', name='twitter:image')
    if twitter_image and twitter_image.get('content'):
        return twitter_image['content']

    # Try to find the first image in the article
    article = soup.find('article')
    if article:
        img = article.find('img')
        if img and img.get('src'):
            return img['src']

    # Try to find images with specific classes
    main_image = soup.find('img', class_=lambda x: x and 'main' in x.lower())
    if main_image and main_image.get('src'):
        return main_image['src']

    return None

def extract_full_content(soup):
    content = ''
    try:
        article = soup.find('article')
        if article:
            content = article.get_text(separator='\n', strip=True)
            return content

        main = soup.find('main')
        if main:
            content = main.get_text(separator='\n', strip=True)
            return content

        content_divs = soup.find_all('div', {'class': lambda x: x and 'content' in x.lower()})
        if content_divs:
            content = '\n'.join([div.get_text(separator='\n', strip=True) for div in content_divs])
            return content

        paragraphs = soup.find_all('p')
        if paragraphs:
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            return content

        return content
    except Exception as e:
        logging.error(f"Error extracting content: {e}")
        return content

def is_irrelevant_link(url):
    return False

if __name__ == "__main__":
    url = "https://apnews.com/article/israel-hezbollah-rocket-attack-mideast-tensions-0584727974096d98d1b5b132dfd1d218"  # Replace with your article URL
    crawler = RaiArticles(url)
    crawler.start()
