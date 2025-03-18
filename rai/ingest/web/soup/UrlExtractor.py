import asyncio
import re
from urllib.parse import urljoin

from F import LIST
from bs4 import BeautifulSoup

class WebUrlExtractor:
    """
    Focused, master-level URL Extractor that merges relative links with a given base URL.
    Returns a list of all discovered URLs.
    """
    def __init__(self, html: str, base_url: str = ""):
        """
        :param html: The raw HTML content.
        :param base_url: The base URL for resolving relative paths.
        """
        self.soup = BeautifulSoup(html, "html.parser")
        self.base_url = base_url

    @classmethod
    def pipeline(cls, html: str, base_url: str = "") -> list[str]:
        """
        Class method to create an instance and immediately run the URL-extraction pipeline.
        :return: A list of extracted URLs.
        """
        instance = cls(html, base_url)
        return instance.run()
    @classmethod
    async def pipeline_async(cls, html) -> list[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls.pipeline, html)

    def run(self) -> list[str]:
        """
        Primary method that triggers the thorough URL extraction and returns a unique list.
        """
        return self._extract_all_urls()

    def _extract_all_urls(self) -> list[str]:
        """
        Scans for every plausible hyperlink or resource URL:
          1) <a href="">
          2) <form action="">
          3) <script src="">
          4) <link href="">
          5) <img src="">
          6) <iframe src="">
          7) <object data="">, <embed src="">
          8) <audio src="">, <video src=""> + <source src="">
          9) <meta http-equiv="refresh" content="...; url=...">
         10) onclick="window.location='...'" or "location.href='...'"
         11) data-* attributes that might hold links
        And merges them with self.base_url as needed.
        """
        all_urls = set()

        # --- 1) Anchors (<a href="...">) ---
        for link in self.soup.find_all('a'):
            href = link.get('href')
            if href:
                all_urls.add(urljoin(self.base_url, href))

        # --- 2) Forms (<form action="...">) ---
        for form in self.soup.find_all('form'):
            action = form.get('action')
            if action:
                all_urls.add(urljoin(self.base_url, action))

        # --- 3) Scripts (<script src="...">) ---
        for script in self.soup.find_all('script'):
            src = script.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))

        # --- 4) Links (<link href="...">) ---
        for link_tag in self.soup.find_all('link'):
            href = link_tag.get('href')
            if href:
                all_urls.add(urljoin(self.base_url, href))

        # --- 5) Images (<img src="...">) ---
        for img in self.soup.find_all('img'):
            src = img.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))

        # --- 6) Iframes (<iframe src="...">) ---
        for iframe in self.soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))

        # --- 7) Object & Embed (<object data="...">, <embed src="...">) ---
        for obj in self.soup.find_all('object'):
            data = obj.get('data')
            if data:
                all_urls.add(urljoin(self.base_url, data))

        for embed in self.soup.find_all('embed'):
            src = embed.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))

        # --- 8) Audio & Video (<audio src="...">, <video src="...">, <source src="...">) ---
        for audio in self.soup.find_all('audio'):
            src = audio.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))

        for video in self.soup.find_all('video'):
            src = video.get('src')
            if src:
                all_urls.add(urljoin(self.base_url, src))
            # <video> can have nested <source src="...">
            for source in video.find_all('source'):
                ssrc = source.get('src')
                if ssrc:
                    all_urls.add(urljoin(self.base_url, ssrc))

        # --- 9) Meta Refresh (<meta http-equiv="refresh" content="...; url=...">) ---
        for meta in self.soup.find_all('meta'):
            if meta.get('http-equiv', '').lower() == 'refresh':
                content = meta.get('content', '')
                match = re.search(r'url=(.*)', content, re.IGNORECASE)
                if match:
                    refresh_url = match.group(1).strip()
                    all_urls.add(urljoin(self.base_url, refresh_url))

        # --- 10) Buttons/Inputs with onclick pointing to navigation (window.location=..., etc.) ---
        pattern = r"(?:window\.location\s*=\s*|location\.href\s*=\s*|location\s*=\s*)(['\"])(.*?)\1"
        for element in self.soup.find_all(['button', 'input']):
            onclick = element.get('onclick') or ''
            match = re.search(pattern, onclick)
            if match:
                nav_url = match.group(2).strip()
                all_urls.add(urljoin(self.base_url, nav_url))

        # --- 11) data-* attributes that might hold a URL (data-href, data-url, etc.) ---
        for element in self.soup.find_all():
            for attr, val in element.attrs.items():
                if isinstance(val, str):
                    # If the attribute ends with 'href', 'src', 'url', 'link', or is suspiciously a link.
                    if attr.lower().endswith(('href', 'src', 'url', 'link')):
                        all_urls.add(urljoin(self.base_url, val))

        table_urls = self.extract_table_links()

        # Return as a list
        return LIST.merge_lists(list(all_urls), table_urls)

    def extract_table_links(self) -> [str]:
        """
        Given raw HTML, finds all tables and extracts every possible URL:
          - Traditional anchor tags (<a href="...">) within <table> or <tr>.
          - 'onclick' handlers that might contain a navigation link.
          - Custom data attributes (e.g., data-href, data-url, etc.) if they appear in table rows or cells.
        Returns a list of absolute URLs (unique).

        :param html: The raw HTML content containing one or more <table> elements.
        :param base_url: The base URL (if any) to resolve relative links. Defaults to empty.
        :return: A list of URLs extracted from all tables.
        """
        extracted_urls = set()

        # 1) Grab all tables in the document
        tables = self.soup.find_all("table")
        for table in tables:
            # --- a) Traditional anchor links (<a href="...">) within the table ---
            for a_tag in table.find_all("a", href=True):
                href = a_tag["href"].strip()
                if href:
                    extracted_urls.add(urljoin(self.base_url, href))

            # --- b) Check for row-level or cell-level onclick patterns, e.g. onclick="window.location='...'". ---
            # A generic regex for capturing URLs in JS code like location.href='...', window.location='...'
            onclick_pattern = r"(?:window\.location\s*=\s*|location\.href\s*=\s*|location\s*=\s*)(['\"])(.*?)\1"

            all_rows = table.find_all("tr")
            for row in all_rows:
                onclick = row.get("onclick", "") or ""
                match = re.search(onclick_pattern, onclick)
                if match:
                    # if there's a match, it's presumably a URL
                    found_url = match.group(2).strip()
                    extracted_urls.add(urljoin(self.base_url, found_url))

                # --- c) Custom data-* attributes (e.g., data-href="..." ) that might store a link ---
                # We check each attribute on the row, searching for potential link values.
                for attr, val in row.attrs.items():
                    if isinstance(val, str):
                        # If the attribute ends with 'href', 'src', 'url', etc., or any pattern you require:
                        if attr.lower().endswith(("href", "src", "url", "link")):
                            extracted_urls.add(urljoin(self.base_url, val))

                # Also, you could do the same for <td> or <th> if those store links in data attributes:
                all_cells = row.find_all(["td", "th"])
                for cell in all_cells:
                    for cattr, cval in cell.attrs.items():
                        if isinstance(cval, str):
                            if cattr.lower().endswith(("href", "src", "url", "link")):
                                extracted_urls.add(urljoin(self.base_url, cval))

        return list(extracted_urls)