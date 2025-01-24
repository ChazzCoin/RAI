import re
from typing import Union

from bs4 import BeautifulSoup, Tag
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from rai.data.web.soup import Search as S

class WebSoupExtractor:
    html = None
    soup = None

    def parse(self, html):
        self.html = html
        self.soup = BeautifulSoup(self.html, 'html.parser')

    def get_body(self): return self.soup.body

    def clean_html_tag(self, tags: [str]) -> str:
        to_remove = [
            "class", "img", "src", "data", "height", "width", "style", "visibility",
            "allow", "id"
        ]
        # Parse the tag string with Beautiful Soup
        cleaned_tags = []
        for tag_str in tags:
            soup = BeautifulSoup(tag_str, 'html.parser')

            # Find the first tag in the parsed soup
            tag = soup.find()

            if tag is None:
                continue

            # Remove specified attributes
            atts = list(tag.attrs.keys())
            for attr in atts:
                if attr in to_remove:
                    del tag.attrs[attr]
                else:
                    for r in to_remove:
                        if str(attr).startswith(r):
                            del tag.attrs[attr]

            # Return the modified tag as a string
            cleaned_tags.append(str(tag))
        return cleaned_tags
    def extract_content(self) -> str:
        content = ''
        all_elements = []

        try:
            # Extract text from paragraphs, headings, blockquotes, and code blocks
            text_elements = self.soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'])

            # Extract text from tables (captions, headers, and cells)
            tables = self.soup.find_all('table')
            for table in tables:
                text_elements.extend(table.find_all(['caption', 'th', 'td']))

            # Extract text from lists
            lists = self.soup.find_all(['ul', 'ol', 'dl'])
            for lst in lists:
                text_elements.extend(lst.find_all(['li', 'dt', 'dd']))

            # Extract text from links and buttons
            interactive_elements = self.soup.find_all(['a', 'button'])
            text_elements.extend(interactive_elements)

            # Extract captions and titles from images (for photo galleries)
            images = self.soup.find_all('img')
            for img in images:
                alt_text = img.get('alt')
                title_text = img.get('title')
                data_caption = img.get('data-caption')  # Example of data-* attribute
                aria_label = img.get('aria-label')
                # Collect all available text attributes
                for attr_text in [alt_text, title_text, data_caption, aria_label]:
                    if attr_text and attr_text.strip():
                        all_elements.append(img)
                        content += attr_text.strip() + '\n'

            # Extract text from modals/popups, including nested ones
            modals = self.soup.find_all('div', class_=re.compile(r'(popup|modal)', re.I))
            for modal in modals:
                modal_text = modal.get_text(separator=' ', strip=True)
                if modal_text:
                    all_elements.append(modal)
                    content += modal_text + '\n'
                # Optionally, handle nested modals recursively
                nested_modals = modal.find_all('div', class_=re.compile(r'(popup|modal)', re.I))
                for nested_modal in nested_modals:
                    nested_text = nested_modal.get_text(separator=' ', strip=True)
                    if nested_text:
                        all_elements.append(nested_modal)
                        content += nested_text + '\n'

            # Extract text from additional meaningful elements
            additional_elements = self.soup.find_all(['span', 'div'],
                                                     class_=re.compile(r'(content|description|summary|article)', re.I))
            text_elements.extend(additional_elements)

            # Extract metadata from <meta> tags
            meta_tags = self.soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('name') in ['description', 'keywords'] and meta.get('content'):
                    all_elements.append(meta)
                    content += meta.get('content').strip() + '\n'

            # Extract text from iframes if necessary
            iframes = self.soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src:
                    # Depending on the use case, you might want to fetch iframe content
                    # Here, we'll just note the iframe source
                    all_elements.append(iframe)
                    content += f"Iframe source: {src}\n"

            # Collect text content from all gathered elements
            for elem in text_elements:
                if isinstance(elem, str):
                    text = elem.strip()
                else:
                    text = elem.get_text(separator=' ', strip=True)
                if text:
                    all_elements.append(elem)
                    content += text + '\n'

            # Remove duplicate lines
            content = '\n'.join(list(dict.fromkeys(content.split('\n'))))

            return {
                'content': self.refine_text_content(content),
                'all_elements': all_elements,
                'all_tags': self.clean_html_tag(tags=[str(tag) for tag in all_elements])
            }
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return {
                'content': self.refine_text_content(content),
                'all_elements': all_elements,
                'all_tags': self.clean_html_tag(tags=[str(tag) for tag in all_elements])
            }
    def extract_lists(self):
        lists = self.soup.find_all(['ul', 'ol', 'dl'])
        items = []
        texts = []
        content = ""
        for lst in lists:
            items.extend(lst.find_all(['li', 'dt', 'dd']))

        for elem in items:
            if isinstance(elem, str):
                text = elem.strip()
            else:
                text = elem.get_text(separator=' ', strip=True)
            if text:
                texts.append(text)
                content += text + '\n'
        return {
            'texts': texts,
            'content': content
        }

    def get_elements(self, tag):
        body_tag = self.soup.body
        if body_tag is None: return []
        return body_tag.find_all(tag, recursive=True)

    def get_paragraphs(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        p_elements = body_tag.find_all("p")
        return [str(p) for p in p_elements]

    def get_tables(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        table_elements = body_tag.find_all("table")
        return [str(tbl) for tbl in table_elements]

    def get_sections(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        section_elements = body_tag.find_all("section")
        return [str(sec) for sec in section_elements]

    def get_headings_h1(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h1_elements = body_tag.find_all("h1")
        return [str(h1) for h1 in h1_elements]

    def get_headings_h2(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h2_elements = body_tag.find_all("h2")
        return [str(h2) for h2 in h2_elements]

    def get_headings_h3(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h3_elements = body_tag.find_all("h3")
        return [str(h3) for h3 in h3_elements]

    def get_headings_h4(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h4_elements = body_tag.find_all("h4")
        return [str(h4) for h4 in h4_elements]

    def get_headings_h5(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h5_elements = body_tag.find_all("h5")
        return [str(h5) for h5 in h5_elements]

    def get_headings_h6(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        h6_elements = body_tag.find_all("h6")
        return [str(h6) for h6 in h6_elements]

    def get_spans(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        span_elements = body_tag.find_all("span")
        return [str(span) for span in span_elements]

    def get_anchors(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        a_elements = body_tag.find_all("a")
        return [str(a) for a in a_elements]

    def get_images(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        img_elements = body_tag.find_all("img")
        return [str(img) for img in img_elements]

    def get_unordered_lists(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        ul_elements = body_tag.find_all("ul")
        return [str(ul) for ul in ul_elements]

    def get_ordered_lists(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        ol_elements = body_tag.find_all("ol")
        return [str(ol) for ol in ol_elements]

    def get_list_items(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        li_elements = body_tag.find_all("li")
        return [str(li) for li in li_elements]

    def get_forms(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        form_elements = body_tag.find_all("form")
        return [str(frm) for frm in form_elements]

    def get_inputs(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        input_elements = body_tag.find_all("input")
        return [str(inp) for inp in input_elements]

    def get_buttons(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        button_elements = body_tag.find_all("button")
        return [str(btn) for btn in button_elements]

    def get_labels(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        label_elements = body_tag.find_all("label")
        return [str(lbl) for lbl in label_elements]

    def get_navs(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        nav_elements = body_tag.find_all("nav")
        return [str(nav) for nav in nav_elements]

    def get_headers(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        header_elements = body_tag.find_all("header")
        return [str(hd) for hd in header_elements]

    def get_footers(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        footer_elements = body_tag.find_all("footer")
        return [str(ft) for ft in footer_elements]

    def get_asides(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        aside_elements = body_tag.find_all("aside")
        return [str(asd) for asd in aside_elements]

    def get_articles(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        article_elements = body_tag.find_all("article")
        return [str(art) for art in article_elements]

    def get_mains(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        main_elements = body_tag.find_all("main")
        return [str(m) for m in main_elements]

    def get_blockquotes(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        blockquote_elements = body_tag.find_all("blockquote")
        return [str(bq) for bq in blockquote_elements]

    def get_strongs(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        strong_elements = body_tag.find_all("strong")
        return [str(s) for s in strong_elements]

    def get_ems(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        em_elements = body_tag.find_all("em")
        return [str(e) for e in em_elements]

    def get_pres(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        pre_elements = body_tag.find_all("pre")
        return [str(pe) for pe in pre_elements]

    def get_codes(self):
        body_tag = self.soup.body
        if body_tag is None:
            return []
        code_elements = body_tag.find_all("code")
        return [str(c) for c in code_elements]

