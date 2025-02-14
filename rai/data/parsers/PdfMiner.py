

import io
import uuid
from io import BytesIO
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import (
    LAParams, LTTextBox, LTTextLine, LTChar, LTFigure, LTImage, LTLine, LTCurve, LTRect,
)
from pdfminer.converter import PDFPageAggregator
from rai.composers.DocumentAnalysisAgent import DocumentAnalysisAgent
from rai.data.loaders.rai_loaders.BaseLoad import RaiDocCreator, RaiLoaderDocument
from rai.data.web.WebModels import TextLineClassification, TextLineDetail


def only_spaces_and_newlines(text):
    """Utility to check if a string is effectively empty."""
    return not text.strip()

class RaiPdfMiner(RaiDocCreator):
        document_id = str(uuid.uuid4())
        page_id = str(uuid.uuid4())
        pages = []
        page_count = 0

        def __init__(self, file_path: str):
            super().__init__(file_path)

        def run(self, file_data=None, file_bytes=None) -> [RaiLoaderDocument]:
            """
            Enhanced PDF parsing:
              - Detect text context changes (headings, headers, footers, chapters)
              - Extract text from images
              - Convert each page into an image byte string
            """

            # -------------------------------------------------
            # 0) Read all PDF bytes upfront (needed for pdf2image)
            # -------------------------------------------------
            if file_data: pdf_bytes = file_data
            elif file_bytes: pdf_bytes = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes
            elif self.file_path:
                with open(self.file_path, 'rb') as f:
                    pdf_bytes = f.read()
            else: return None

            # -------------------------------------------------
            # 1) Convert PDF to a list of PIL Images (one image per page)
            # -------------------------------------------------
            try:
                pil_pages = convert_from_bytes(pdf_bytes, dpi=150)
                # Adjust dpi if needed for clarity
            except Exception as e:
                print(f"Error converting PDF to images: {e}")
                return None

            # -------------------------------------------------
            # 2) Setup PDFMiner resources
            # -------------------------------------------------
            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            # Re-wrap pdf_bytes in BytesIO for PDFMiner parsing
            fp = BytesIO(pdf_bytes)

            pages_data = []
            self.page_count = 1
            # -------------------------------------------------
            # Helper: Determine text attributes (e.g. heading, header, footer, chapters)
            # -------------------------------------------------
            def classify_textline(obj, page_height, font_size_threshold=12) -> TextLineClassification:
                x0, y0, x1, y1 = obj.bbox
                # Heuristic for header/footer (top/bottom ~10% of page height)
                header_cutoff = page_height * 0.9
                footer_cutoff = page_height * 0.1

                # Calculate max font size in this line
                max_font_size = 0
                for c in obj._objs:
                    if isinstance(c, LTChar):
                        max_font_size = max(max_font_size, getattr(c, 'size', 0))

                text_content = obj.get_text().strip()
                is_header = (y0 > header_cutoff)
                is_footer = (y1 < footer_cutoff)
                is_heading = (max_font_size > font_size_threshold)
                # Naive chapter detection if line starts with 'Chapter' and font is large
                # Expand or refine logic as needed
                lower_text = text_content.lower()
                is_chapter = (("chapter" in lower_text[:10]) and is_heading)

                return TextLineClassification(
                    header=is_header,
                    footer=is_footer,
                    chapter=is_chapter,
                )

            # -------------------------------------------------
            # 3) Parse each page with PDFMiner
            # -------------------------------------------------
            for page in PDFPage.get_pages(fp, caching=True, check_extractable=True):
                # Process the page
                interpreter.process_page(page)
                layout = device.get_result()

                page_height = layout.bbox[3]  # typically (0,0,x2,y2), y2 is page height

                # Collect text lines (with classification) and images for this page
                line_items = []
                extracted_images_text = []

                def parse_layout_objects(l_objs):
                    """Recursively parse layout objects (text boxes, lines, images, figures)."""
                    for obj in l_objs:

                        if isinstance(obj, (LTTextBox, LTTextLine)):
                            text_str = obj.get_text()
                            if not only_spaces_and_newlines(text_str):
                                # Classify line type
                                line_class: TextLineClassification = classify_textline(obj, page_height)
                                line_items.append(TextLineDetail(
                                    text=text_str,
                                    classification=line_class,
                                ))

                        elif isinstance(obj, LTImage):
                            # Attempt OCR on the image
                            try:
                                img_data = obj.stream.get_data()
                                image_stream = BytesIO(img_data)
                                with Image.open(image_stream) as pil_img:
                                    extracted_text = pytesseract.image_to_string(pil_img)
                                    if extracted_text.strip():
                                        extracted_images_text.append(extracted_text)
                            except Exception as e:
                                # If OCR fails or the image is not valid
                                print(f"Image OCR error (page {self.page_count+1}): {e}")
                                pass

                        elif isinstance(obj, LTFigure):
                            # Recursively process figures
                            parse_layout_objects(obj._objs)

                # Parse all items in the layout
                parse_layout_objects(layout._objs)

                # -------------------------------------------------
                # Convert this PDF page to a byte string (PNG)
                # using the corresponding pil_pages[self.page_count]
                # -------------------------------------------------
                page_image_bytes = b""
                try:
                    with BytesIO() as img_buf:
                        pil_pages[self.page_count].save(img_buf, format='PNG')
                        page_image_bytes = img_buf.getvalue()
                except Exception as e:
                    print(f"Could not convert page {self.page_count+1} to image bytes: {e}")

                """ Entire Page of Text """
                # combined_text = "\n".join([li.text for li in line_items])

                """ Body of Text Only """
                body = []
                for li in line_items:
                    if li.classification.header: continue
                    elif li.classification.footer: continue
                    body.append(li.text)
                body_text = "\n".join(body)

                """ Page Extraction Model """
                page = DocumentAnalysisAgent.analyze_text_async(
                    content=body_text,
                    image=page_image_bytes,
                    file=self.file_path,
                    file_type='pdf',
                    parent_id=self.document_id,
                    page_id=self.page_id,
                    page_number=str(self.page_count),
                )
                page.author = "RaiPdfMiner"
                page.title = self.file_path if self.file_path else "bytes"
                page.file = self.file_path if self.file_path else "bytes"
                page.page_count = str(self.page_count + 1)
                page.lines = line_items
                page.images_content = extracted_images_text
                page.file_image = page_image_bytes

                """ Add Page, Continue... """
                self.pages.append(page)
                self.to_documents(page)
                self.page_count += 1
                self.page_id = str(uuid.uuid4())

            # Clean up
            fp.close()
            device.close()

            return self.cache


def extract_everything_from_pdf(file_path=None, file_data=None, file_bytes=None):
    # pdfminer setup
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()  # Tweak for better text layout, e.g. char_margin, line_margin, etc.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    # Decide how to get our file-like object
    if file_data:
        fp = io.BytesIO(file_data)
    elif file_bytes:
        fp = file_bytes
    elif file_path:
        fp = open(file_path, 'rb')
    else:
        return None

    all_pages_data = []
    page_number = 0

    # Process each page in the PDF
    for page in PDFPage.get_pages(fp, caching=True, check_extractable=True):
        page_number += 1

        interpreter.process_page(page)
        layout = device.get_result()

        # Basic page size from PDFPage (in many PDFs, mediabox defines these)
        page_width = page.mediabox[2] - page.mediabox[0]
        page_height = page.mediabox[3] - page.mediabox[1]

        page_data = {
            "page_number": page_number,
            "width": page_width,
            "height": page_height,
            "elements": []
        }

        # Recursive function to parse layout objects
        def parse_layout_objects(l_objs, elements_list):
            for obj in l_objs:
                # TEXT
                if isinstance(obj, (LTTextBox, LTTextLine)):
                    # All the text lines/boxes
                    elements_list.append({
                        "type": "text",
                        "bbox": obj.bbox,
                        "text": obj.get_text().rstrip("\n")  # or keep trailing newlines if you prefer
                    })
                    # If you want to go deeper to char level inside a line or box:
                    for child in getattr(obj, "_objs", []):
                        if isinstance(child, LTChar):
                            elements_list.append({
                                "type": "char",
                                "bbox": child.bbox,
                                "text": child.get_text()
                            })

                # IMAGES
                elif isinstance(obj, LTImage):
                    # Attempt to get raw image bytes
                    try:
                        img_data = obj.stream.get_data()
                    except Exception:
                        img_data = None
                    elements_list.append({
                        "type": "image",
                        "bbox": obj.bbox,
                        "data": img_data
                    })

                # SHAPES (Line, Rect, Curve)
                elif isinstance(obj, LTLine):
                    elements_list.append({
                        "type": "line",
                        "bbox": obj.bbox,
                        "linewidth": obj.linewidth
                    })
                elif isinstance(obj, LTRect):
                    elements_list.append({
                        "type": "rect",
                        "bbox": obj.bbox,
                        "linewidth": obj.linewidth
                    })
                elif isinstance(obj, LTCurve):
                    elements_list.append({
                        "type": "curve",
                        "bbox": obj.bbox,
                        "linewidth": obj.linewidth,
                        # LTCurve might have points that define it
                        "pts": [(pt[0], pt[1]) for pt in obj.get_pts()]
                    })

                # FIGURES (can contain nested elements, so recurse)
                elif isinstance(obj, LTFigure):
                    figure_data = {
                        "type": "figure",
                        "bbox": obj.bbox,
                        "elements": []
                    }
                    elements_list.append(figure_data)
                    # Recurse into figure to capture child objects
                    parse_layout_objects(obj._objs, figure_data["elements"])

                else:
                    # Catch-all for unhandled objects
                    elements_list.append({
                        "type": "unknown",
                        "bbox": getattr(obj, "bbox", None),
                        "info": str(obj)
                    })

        # Parse objects at the top level of the page layout
        parse_layout_objects(layout._objs, page_data["elements"])

        all_pages_data.append(page_data)

    fp.close()
    device.close()

    return all_pages_data

if __name__ == '__main__':
    from F import OS
    cwd = OS.get_cwd()
    file = "/Users/chazzromeo/Desktop/pcsc2024/general/USSoccerPositionNumbersandProfilespdf.pdf"
    result = RaiPdfMiner(file_path=file).run()
    print(result)