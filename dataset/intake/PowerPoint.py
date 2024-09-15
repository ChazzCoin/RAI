from pptx import Presentation
from config import default_file_path
from files.FilePath import FilePath
from files.save import DataSaver


def pptx_to_txt_file(pptx_file, output_text_file:FilePath):
    # Open the presentation
    presentation = Presentation(pptx_file)
    # Initialize an empty list to hold the extracted text
    text_runs = []
    # Loop through each slide in the presentation
    for slide in presentation.slides:
        # Loop through each shape in the slide
        for shape in slide.shapes:
            # Check if the shape contains text
            if hasattr(shape, "text"):
                text_runs.append(shape.text)
    # Write the extracted text to the output text file
    DataSaver.save_txt(data=text_runs, output=output_text_file)
    print(f"Text successfully extracted to {output_text_file}")

if __name__ == "__main__":
    # Example usage
    pptx_file_path = "/Users/chazzromeo/Desktop/parkcitysoccer/PCSC Pre-Placement May 5, 2024.pptx"
    output_text_file_path = f"{default_file_path()}/pptx-test.txt"
    pptx_to_txt_file(pptx_file_path, output_text_file_path)
