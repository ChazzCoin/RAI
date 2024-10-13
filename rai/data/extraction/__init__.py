import os
import tempfile
import traceback
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

def extract_handwritten_text_from_pdf(pdf_path):
    """
    Extracts handwritten text from a PDF file using Hugging Face's TrOCR model.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from the PDF.
    """
    try:
        # Check if the PDF file exists
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"The file {pdf_path} does not exist.")

        # Convert PDF pages to images with higher DPI for better resolution
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt='png', dpi=300)
            print(f"Number of pages converted to images: {len(images)}")

            if not images:
                raise ValueError("No images were extracted from the PDF file.")

            # Save images for inspection
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                image.save(image_path)
                print(f"Saved image: {image_path}")

            # Load the pre-trained TrOCR model and processor for handwritten text
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Using device: {device}")

            # Use the larger model variant
            processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-handwritten')
            model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-handwritten').to(device)
            model.eval()

            extracted_text = ""

            for i, image in enumerate(images):
                print(f"Processing page {i+1}/{len(images)}...")

                # Ensure image is in RGB mode
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # Enhance image quality
                image = image.convert('L')  # Convert to grayscale

                # Binarize the image
                threshold = 150
                image = image.point(lambda p: p > threshold and 255)

                # Resize the image
                new_size = (image.width * 2, image.height * 2)
                image = image.resize(new_size, Image.DEFAULT_STRATEGY)

                # Preprocess image
                pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

                # Generate text with adjusted parameters
                with torch.no_grad():
                    generated_ids = model.generate(pixel_values, max_new_tokens=50)
                generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                print(f"Generated text for page {i+1}: '{generated_text}'")

                extracted_text += generated_text + "\n\n"

            return extracted_text.strip() if extracted_text.strip() else None

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Example usage
    pdf_file_path = "/Users/chazzromeo/Desktop/data/development/Doc2.pdf"  # Replace with your PDF file path
    text = extract_handwritten_text_from_pdf(pdf_file_path)
    if text:
        print("Extracted Text:")
        print(text)
    else:
        print("No text could be extracted.")
