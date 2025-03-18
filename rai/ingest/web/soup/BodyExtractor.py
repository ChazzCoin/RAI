import asyncio

from rai.ingest.web.soup.WebExtractor import WebSoupExtractor
from rai.ingest.web.WebModels import ContentGroup, WebBodyModel
from bs4 import Comment

class WebBodyExtractor(WebSoupExtractor):

    def __init__(self, html):
        super().__init__()
        self.parse(html)

    @classmethod
    def pipeline(cls, html) -> WebBodyModel:
        newCls = cls(html)
        return newCls.run()

    @classmethod
    async def pipeline_async(cls, html) -> WebBodyModel:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls.pipeline, html)

    @staticmethod
    def refine_text_content(text: str) -> str: return text.strip()
    @staticmethod
    def combine_body_paragraphs(paragraphs: []) -> str:
        paragraph_texts = []
        for group in paragraphs:
            text = group.content.strip()
            if text:
                paragraph_texts.append(text)
        combined_text = "\n\n".join(paragraph_texts)
        return combined_text


    def extract_content(self):
        content = ''
        try:
            # Extract text from paragraphs and headings
            text_elements = self.soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            # Extract text from tables
            tables = self.soup.find_all('table')
            for table in tables:
                text_elements.extend(table.find_all(['caption', 'td', 'th']))
            # Extract captions from images (for photo galleries)
            images = self.soup.find_all('img')
            for img in images:
                alt_text = img.get('alt')
                title_text = img.get('title')
                if alt_text:
                    content += alt_text + '\n'
                elif title_text:
                    content += title_text + '\n'
            # Extract text from lists
            lists = self.soup.find_all(['ul', 'ol'])
            for lst in lists:
                text_elements.extend(lst.find_all('li'))
            # Extract text from other common popups or modals
            modals = self.soup.find_all('div', {'class': lambda x: x and ('popup' in x or 'modal' in x)})
            for modal in modals:
                modal_text = modal.get_text(separator=' ', strip=True)
                if modal_text:
                    content += modal_text + '\n'
            # Collect text content
            for elem in text_elements:
                text = elem.get_text(separator=' ', strip=True)
                if text:
                    content += text + '\n'
            return self.refine_text_content(content)
        except Exception as e:
            print(f"Error extracting content: {str(e)}")
            return self.refine_text_content(content)
    def run(self) -> WebBodyModel:
        """
        Extracts all relevant content from the <body> of the current page
        and returns a BodyModelObject with grouped data + metadata.
        """
        try:
            # --- PREPARE LISTS TO HOLD EXTRACTED GROUPS ---
            heading_groups = []
            paragraph_groups = []
            table_groups = []
            image_groups = []
            list_groups = []
            modal_groups = []
            tile_groups = []

            combined_content = ""

            # Extract headings (h1-h6)
            headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for h in headings:
                text = h.get_text(separator=' ', strip=True)
                if text:
                    # Add to combined text
                    combined_content += text + '\n'
                    heading_groups.append(ContentGroup(
                        content=text,
                        metadata={
                            "tag": h.assistant,
                            "class": ' '.join(h.get('class', []))
                        }
                    ))

            # Extract paragraphs
            # Define your threshold for a "short" paragraph.
            SHORT_THRESHOLD = 100  # Adjust this value based on your needs

            paragraphs = self.soup.find_all('p')
            combined_content = ""
            paragraph_groups = []

            i = 0
            while i < len(paragraphs):
                # Grab the text of the current paragraph.
                p = paragraphs[i]
                current_text = p.get_text(separator=' ', strip=True)
                if not current_text:
                    i += 1
                    continue

                # Start with the current text as the combined block.
                combined_text = current_text

                # If the current paragraph is short, look ahead and attach to the following paragraph(s)
                while len(current_text) < SHORT_THRESHOLD and i < len(paragraphs) - 1:
                    i += 1
                    next_p = paragraphs[i]
                    next_text = next_p.get_text(separator=' ', strip=True)
                    if not next_text:
                        continue
                    # Append the next paragraph's text to the combined text.
                    # Note: We prefix the next paragraph with the current short text.
                    combined_text = combined_text + " " + next_text

                    # Check the length of the "next_text" individually.
                    current_text = next_text

                # Append the combined block to our overall content and to our structured list.
                combined_content += combined_text + '\n'
                paragraph_groups.append(ContentGroup(
                    content=combined_text,
                    metadata={
                        "tag": "p",
                        "class": ' '.join(p.get('class', []))
                    }
                ))
                i += 1
            formatted_paragraph_content = self.combine_body_paragraphs(paragraph_groups)
            # Extract tables
            tables = self.soup.find_all('table')
            for table in tables:
                table_text = table.get_text(separator=' ', strip=True)
                if table_text:
                    combined_content += table_text + '\n'
                    table_groups.append(ContentGroup(
                        content=table_text,
                        metadata={
                            "tag": 'table',
                            "class": ' '.join(table.get('class', []))
                        }
                    ))

            # Extract images (alt/title)
            images = self.soup.find_all('img')
            for img in images:
                alt_text = img.get('alt')
                title_text = img.get('title')
                # We'll store whichever text we find (prefer alt over title)
                if alt_text or title_text:
                    chosen_text = alt_text if alt_text else title_text
                    combined_content += chosen_text + '\n'
                    image_groups.append(ContentGroup(
                        content=chosen_text,
                        metadata={
                            "tag": 'img',
                            "src": img.get('src', ''),
                            "class": ' '.join(img.get('class', []))
                        }
                    ))

            # Extract lists (ul/ol) and their <li> items
            lists = self.soup.find_all(['ul', 'ol'])
            for lst in lists:
                # We could store the entire list as one group or each <li> individually
                list_items_text = []
                li_tags = lst.find_all('li')
                for li in li_tags:
                    li_text = li.get_text(separator=' ', strip=True)
                    if li_text:
                        list_items_text.append(li_text)

                if list_items_text:
                    # Join them, or store them as an array
                    combined_content += '\n'.join(list_items_text) + '\n'
                    list_groups.append(ContentGroup(
                        content='\n'.join(list_items_text),
                        metadata={
                            "tag": lst.assistant,
                            "class": ' '.join(lst.get('class', [])),
                            "li_count": str(len(list_items_text))
                        }
                    ))

            # Extract modals/popup content
            modals = self.soup.find_all('div', {
                'class': lambda x: x and ('popup' in x or 'modal' in x)
            })
            for modal in modals:
                modal_text = modal.get_text(separator=' ', strip=True)
                if modal_text:
                    combined_content += modal_text + '\n'
                    modal_groups.append(ContentGroup(
                        content=modal_text,
                        metadata={
                            "tag": 'div',
                            "class": ' '.join(modal.get('class', []))
                        }
                    ))

            # Extract "tiles" or "cards" (example)
            tiles = self.soup.find_all('div', {
                'class': lambda x: x and ('tile' in x or 'card' in x)
            })
            for t in tiles:
                tile_text = t.get_text(separator=' ', strip=True)
                if tile_text:
                    combined_content += tile_text + '\n'
                    tile_groups.append(ContentGroup(
                        content=tile_text,
                        metadata={
                            "tag": 'div',
                            "class": ' '.join(t.get('class', []))
                        }
                    ))

            body_data = WebBodyModel(
                headings=heading_groups,
                paragraphs=paragraph_groups,
                tables=table_groups,
                images=image_groups,
                lists=list_groups,
                modals=modal_groups,
                tiles=tile_groups,
                combined_text=self.extract_body_content()
            )

            return body_data
        except Exception as e:
            print(e)
            return WebBodyModel()

    def extract_body_content(self) -> dict:
        soup = self.soup
        html = self.html

        # Remove comments to avoid hidden or non-visible content
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove tags that generally contain non-relevant content
        unwanted_tags = ["script", "style", "noscript", "iframe", "header", "footer", "nav", "form", "button"]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        # If a <body> tag is present, focus on it; otherwise, process the whole document
        body = soup.body if soup.body else soup

        # Extract text content with newlines separating blocks for readability
        text = body.get_text(separator="\n", strip=True)

        # Extract hyperlinks with their text; ignore empty links
        links = []
        for a in body.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            href = a["href"]
            # Optionally filter out irrelevant links here if needed
            if href and link_text:
                links.append({"href": href, "text": link_text})

        # Extract images and gather src with alt text
        images = []
        for img in body.find_all("img", src=True):
            src = img["src"]
            alt = img.get("alt", "").strip()
            images.append({"src": src, "alt": alt})

        # Extract tables as raw HTML strings for further processing if required
        tables = []
        for table in body.find_all("table"):
            tables.append(str(table))

        return text
