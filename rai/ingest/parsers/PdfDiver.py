import uuid

import pytesseract
from concurrent.futures import ThreadPoolExecutor, as_completed
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import (
    LAParams, LTTextBox, LTTextLine, LTChar, LTFigure, LTImage, LTLine, LTRect,
)
from pdfminer.converter import PDFPageAggregator
from io import BytesIO

from rai.ingest.IngestModels import IngestBrief, TextLineDetail, TextLineClassification
from rai.ingest.providers.WebSourceProvider import validate_and_prepare_screenshot
from rai.ingest.utilities.TextUtils import TextProcessor
import io
from typing import List, Union
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image


def convert_pdf_to_images(pdf_input: Union[str, bytes], dpi: int = 200, fmt: str = "PNG") -> List[bytes]:
    try:
        # Convert the PDF pages into PIL Image objects.
        if isinstance(pdf_input, str):
            # Assumes a file path
            pages = convert_from_path(pdf_input, dpi=dpi)
        elif isinstance(pdf_input, bytes):
            pages = convert_from_bytes(pdf_input, dpi=dpi)
        else:
            raise ValueError("pdf_input must be a file path (str) or raw bytes.")
    except Exception as e:
        raise ValueError(f"Failed to convert PDF to images: {e}")

    image_bytes_list = []
    # Convert each page image to a byte string.
    for page in pages:
        try:
            buf = io.BytesIO()
            page.save(buf, format=fmt)
            image_bytes = buf.getvalue()
            image_bytes_list.append(image_bytes)
            buf.close()
        except Exception as e:
            raise ValueError(f"Failed to convert page to {fmt} bytes: {e}")

    return image_bytes_list


def only_spaces_and_newlines(text: str) -> bool:
    """Utility to check if a string is effectively empty."""
    return not text.strip()


class RaiPdfDiver(TextProcessor):

    pdf_file:str = None
    pdf_bytes:bytes = None

    document_id = str(uuid.uuid4())
    page_id = str(uuid.uuid4())
    briefings = []
    page_images = []
    page_count = 0
    record = {}

    @classmethod
    def load_pdf(cls, pdf: Union[str, bytes]) -> "RaiPdfDiver":
        self = cls()
        if isinstance(pdf, str):
            self.pdf_file = pdf
            with open(pdf, 'rb') as f:
                self.pdf_bytes = f.read()
        else:
            self.pdf_bytes = pdf
        return self

    def run(self):
        """
        Process a PDF by:
          1) Converting the PDF into page images.
          2) Parsing each page concurrently for text (and classifying text lines as header, footer, or body).
          3) Extracting OCR text from any images encountered.

        Returns:
            A dictionary (self.book) with keys as page numbers and values as extracted page data.
        """
        # --- Step 1: Convert PDF pages to images ---
        self.page_images = convert_pdf_to_images(self.pdf_bytes, dpi=150)

        # Create a BytesIO stream from the PDF bytes and load all pages into a list.
        fp = BytesIO(self.pdf_bytes)
        pages = list(PDFPage.get_pages(fp, caching=True, check_extractable=True))

        def process_page(page_tuple) -> IngestBrief:
            """
            Worker function to process a single PDF page.
            Each thread creates its own PDFMiner resource manager, device, and interpreter.
            """
            page, page_index = page_tuple
            local_rsrcmgr = PDFResourceManager()
            local_laparams = LAParams()
            local_device = PDFPageAggregator(local_rsrcmgr, laparams=local_laparams)
            local_interpreter = PDFPageInterpreter(local_rsrcmgr, local_device)

            local_interpreter.process_page(page)
            layout = local_device.get_result()
            page_height = layout.bbox[3]

            # Extract text lines (and OCR any images)
            text_details, _ = self._extract_text_lines_from_layout(layout._objs, page_height)
            body_text = self._filter_body_text(text_details)
            tables = self._extract_tables_from_layout(layout._objs)
            # Retrieve the page image if available
            page_image = self.page_images[page_index] if page_index < len(self.page_images) else None

            content_validation = self.content_is_valid(body_text)
            local_device.close()

            return page_index, IngestBrief(
                source=str(self.pdf_file),
                success=content_validation,
                index=page_index,
                original_content=str(body_text),
                content=TextProcessor.NORMALIZE_NEW_LINES(body_text),
                page_screenshot=page_image
            )


        results = {}
        # --- Step 2: Process pages concurrently ---
        with ThreadPoolExecutor() as executor:
            future_to_index = {
                executor.submit(process_page, (page, idx)): idx
                for idx, page in enumerate(pages)
            }
            for future in as_completed(future_to_index):
                try:
                    page_index, page_result = future.result()
                    results[page_index] = page_result
                except Exception as e:
                    idx = future_to_index[future]
                    print(f"Error processing page {idx}: {e}")

        # --- Step 3: Assemble the final book ---
        self.briefings = [item for item in results.values()]
        fp.close()
        return self.briefings

    def _extract_text_lines_from_layout(self, layout_objects, page_height):
        """
        Recursively parse layout objects and extract text lines and OCR text from images.

        Returns:
            text_details (list[TextLineDetail]): List of extracted text details.
            extracted_images_text (list[str]): List of text strings extracted via OCR from images.
        """
        text_details = []
        extracted_images_text = []

        for obj in layout_objects:
            if isinstance(obj, (LTTextBox, LTTextLine)):
                text_str = obj.get_text()
                if not only_spaces_and_newlines(text_str):
                    classification = self._classify_textline(obj, page_height)
                    text_details.append(TextLineDetail(
                        text=text_str,
                        classification=classification
                    ))
            elif isinstance(obj, LTImage):
                try:
                    img_data = obj.stream.get_data()
                    image_stream = BytesIO(img_data)
                    with Image.open(image_stream) as pil_img:
                        ocr_text = pytesseract.image_to_string(pil_img)
                        if ocr_text.strip():
                            extracted_images_text.append(ocr_text)
                except Exception as e:
                    print(f"Image OCR error: {e}")
            elif isinstance(obj, LTFigure):
                # Recursively process nested figures
                sub_text_details, sub_images_text = self._extract_text_lines_from_layout(obj._objs, page_height)
                text_details.extend(sub_text_details)
                extracted_images_text.extend(sub_images_text)

        return text_details, extracted_images_text
    def _classify_textline(self, obj, page_height, font_size_threshold=12) -> TextLineClassification:
        """
        Classify a text line as header, footer, or chapter/heading based on its position and font size.
        """
        x0, y0, x1, y1 = obj.bbox
        header_cutoff = page_height * 0.9  # top 10% as header
        footer_cutoff = page_height * 0.1  # bottom 10% as footer

        max_font_size = 0
        for c in getattr(obj, '_objs', []):
            if isinstance(c, LTChar):
                max_font_size = max(max_font_size, getattr(c, 'size', 0))

        text_content = obj.get_text().strip()
        is_header = y0 > header_cutoff
        is_footer = y1 < footer_cutoff
        is_heading = max_font_size > font_size_threshold
        # Naively mark as a chapter if the line starts with 'chapter' and is heading-sized.
        is_chapter = "chapter" in text_content.lower()[:10] and is_heading

        return TextLineClassification(
            header=is_header,
            footer=is_footer,
            chapter=is_chapter,
        )
    def _filter_body_text(self, text_details):
        """
        Filters out header and footer text lines and returns the concatenated body text.
        """
        body_lines = [
            detail.text for detail in text_details
            if not (detail.classification.header or detail.classification.footer)
        ]
        return "\n".join(body_lines)
    def _extract_tables_from_layout(self, layout_objects) -> list:
        """
        Heuristically extract table structures from layout objects by analyzing line (LTLine)
        and rectangle (LTRect) objects.
        Returns a list of table dictionaries with cells defined by bounding boxes and any contained text.
        """
        horizontal_lines = []
        vertical_lines = []
        rects = []

        def recurse(objs):
            nonlocal horizontal_lines, vertical_lines, rects
            for obj in objs:
                if isinstance(obj, LTLine):
                    x0, y0, x1, y1 = obj.bbox
                    # If the line is wider than it is tall, assume horizontal.
                    if abs(y1 - y0) < abs(x1 - x0):
                        horizontal_lines.append(obj)
                    else:
                        vertical_lines.append(obj)
                elif isinstance(obj, LTRect):
                    rects.append(obj)
                elif isinstance(obj, LTFigure):
                    recurse(obj._objs)

        recurse(layout_objects)

        tables = []
        # Heuristic: if there are multiple horizontal and vertical lines, consider them as potential table borders.
        if len(horizontal_lines) >= 2 and len(vertical_lines) >= 2:
            # Sort horizontal lines by their vertical (y) position (top to bottom)
            horizontal_lines_sorted = sorted(horizontal_lines, key=lambda l: l.bbox[1], reverse=True)
            # Sort vertical lines by their horizontal (x) position (left to right)
            vertical_lines_sorted = sorted(vertical_lines, key=lambda l: l.bbox[0])

            # Derive unique coordinates (using the midpoints of lines)
            y_coords = sorted({round((line.bbox[1] + line.bbox[3]) / 2, 2) for line in horizontal_lines_sorted}, reverse=True)
            x_coords = sorted({round((line.bbox[0] + line.bbox[2]) / 2, 2) for line in vertical_lines_sorted})

            cells = []
            # Define cells as the regions between adjacent horizontal and vertical lines
            for i in range(len(y_coords) - 1):
                for j in range(len(x_coords) - 1):
                    # Cell bbox: (left, bottom, right, top)
                    cell_bbox = (x_coords[j], y_coords[i+1], x_coords[j+1], y_coords[i])
                    cell_text = self._extract_text_from_bbox(layout_objects, cell_bbox)
                    cells.append({
                        "bbox": cell_bbox,
                        "text": cell_text
                    })
            if cells:
                tables.append({"cells": cells})

        # As an alternate heuristic, use any detected rectangles as potential table cells.
        if rects:
            table_cells = []
            for rect in rects:
                cell_bbox = rect.bbox
                cell_text = self._extract_text_from_bbox(layout_objects, cell_bbox)
                table_cells.append({
                    "bbox": cell_bbox,
                    "text": cell_text
                })
            if table_cells:
                tables.append({"cells": table_cells})

        return tables
    def _extract_text_from_bbox(self, layout_objects, bbox) -> str:
        """
        Recursively extract text from layout objects that intersect with a given bounding box.
        """
        extracted_text = []

        def recurse(objs):
            for obj in objs:
                if isinstance(obj, (LTTextBox, LTTextLine)):
                    # If the object's bbox overlaps sufficiently with the cell bbox, extract its text.
                    if self._bbox_intersect(obj.bbox, bbox):
                        extracted_text.append(obj.get_text().strip())
                elif isinstance(obj, LTFigure):
                    recurse(obj._objs)

        recurse(layout_objects)
        return " ".join(extracted_text)
    def _bbox_intersect(self, bbox1, bbox2, threshold=0.1) -> bool:
        """
        Determine if two bounding boxes intersect significantly.
        bbox format: (x0, y0, x1, y1)
        Returns True if the area of intersection divided by the area of bbox1 exceeds the threshold.
        """
        x0 = max(bbox1[0], bbox2[0])
        y0 = max(bbox1[1], bbox2[1])
        x1 = min(bbox1[2], bbox2[2])
        y1 = min(bbox1[3], bbox2[3])
        if x1 <= x0 or y1 <= y0:
            return False
        intersection_area = (x1 - x0) * (y1 - y0)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        if area1 == 0:
            return False
        return (intersection_area / area1) > threshold



# --- Usage Example ---
if __name__ == '__main__':
    # Example with a file path
    pdf_file_path = "/Users/chazzromeo/Desktop/DocumentTestSet/structured-1.pdf"
    try:
        diver = RaiPdfDiver.load_pdf(pdf_file_path)
        briefs = diver.run()
        print(briefs)
    except Exception as error:
        print("Error:", error)

