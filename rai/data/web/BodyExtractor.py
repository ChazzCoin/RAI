from rai.data.web.WebExtractor import WebSoupExtractor
from rai.data.web.WebModels import ContentGroup, WebBodyModel

class WebBodyExtractor(WebSoupExtractor):

    def __init__(self, html):
        super().__init__(html)

    @classmethod
    def pipeline(cls, html) -> WebBodyModel:
        newCls = cls(html)
        return newCls.run()

    @staticmethod
    def refine_text_content(text: str) -> str: return text.strip()
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
                            "tag": h.name,
                            "class": ' '.join(h.get('class', []))
                        }
                    ))

            # Extract paragraphs
            paragraphs = self.soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                if text:
                    combined_content += text + '\n'
                    paragraph_groups.append(ContentGroup(
                        content=text,
                        metadata={
                            "tag": 'p',
                            "class": ' '.join(p.get('class', []))
                        }
                    ))

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
                            "tag": lst.name,
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

            refined = self.refine_text_content(combined_content)

            body_data = WebBodyModel(
                headings=heading_groups,
                paragraphs=paragraph_groups,
                tables=table_groups,
                images=image_groups,
                lists=list_groups,
                modals=modal_groups,
                tiles=tile_groups,
                combined_text=refined
            )

            return body_data
        except Exception as e:
            print(e)
            return WebBodyModel()


