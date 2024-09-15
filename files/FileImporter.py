import os
from dataset.intake import Excel, Pdf, PowerPoint, Word
from files.FilePaths import FilePaths
from F import OS

def process_file_to_pending(file_name):
    try:
        # Get the file extension
        root = FilePaths.PENDING
        file_ext = os.path.splitext(file_name)[1]
        # Check if the file has the target extension
        if file_ext.lower() == '.pdf':
            file_path = os.path.join(root, file_name)
            print(f"Processing file: {file_path}")
            try:
                Pdf.pdf_to_txt_file(file_path, file_name)
            except Exception as e:
                print(f"Error extracting data from {file_name}: {e}")
        elif file_ext.lower() == '.docx':
            file_path = os.path.join(root, file_name)
            print(f"Processing file: {file_path}")
            try:
                Word.word_to_txt_file(file_path, file_name)
            except Exception as e:
                print(f"Error extracting data from {file_name}: {e}")
        elif file_ext.lower() == '.pptx':
            file_path = os.path.join(root, file_name)
            print(f"Processing file: {file_path}")
            try:
                PowerPoint.pptx_to_txt_file(file_path, file_name)
            except Exception as e:
                print(f"Error extracting data from {file_name}: {e}")
        elif file_ext.lower() == '.xlsx':
            file_path = os.path.join(root, file_name)
            print(f"Processing file: {file_path}")
            try:
                Excel.excel_to_txt_file(file_path, file_name)
            except Exception as e:
                print(f"Error extracting data from {file_name}: {e}")
    except Exception as e:
        print(f"Error extracting data from {file_name}: {e}")



""" Converts Files into basic .txt files for Chroma Intake """
def convert_files_to_txt(import_dir, output_dir):
    """
    Loops through all files in the import directory, checks the file extension,
    and applies the given extraction function if the extension matches.
    Saves the resulting .txt file in the output directory.
    """

    # Check if the import directory exists
    if not os.path.isdir(import_dir):
        print(f"Error: The import directory {import_dir} does not exist.")
        return

    # Ensure the output directory exists, create it if it doesn't
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Output directory {output_dir} created.")
        except Exception as e:
            print(f"Error creating output directory {output_dir}: {e}")
            return

    # Loop through all files in the import directory
    for file_path in FilePaths.loop_directory(import_dir):
        # for file_name in files:
        try:
            if OS.is_directory(file_path):
                continue
            # Get the file extension
            file_name = FilePaths.get_file_name(file_path)
            file_ext = os.path.splitext(file_name)[1]
            # Construct full file path for the input file
            # file_path = FilePaths(os.path.join(root, file_name))
            print(f"Processing file: {file_path}")

            # Handle each file type and generate the output path
            output_file_path = FilePaths(os.path.join(output_dir, os.path.splitext(file_name)[0] + '.txt'))

            if file_ext.lower() == '.pdf':
                try:
                    Pdf.pdf_to_txt_file(file_path, output_file_path)
                    print(f"Saved .txt to: {output_file_path}")
                except Exception as e:
                    print(f"Error extracting data from {file_name}: {e}")
                    continue
            elif file_ext.lower() == '.docx':
                try:
                    Word.word_to_txt_file(file_path, output_file_path)
                    print(f"Saved .txt to: {output_file_path}")
                except Exception as e:
                    print(f"Error extracting data from {file_name}: {e}")
                    continue
            elif file_ext.lower() == '.pptx':
                try:
                    PowerPoint.pptx_to_txt_file(file_path, output_file_path)
                    print(f"Saved .txt to: {output_file_path}")
                except Exception as e:
                    print(f"Error extracting data from {file_name}: {e}")
                    continue
            elif file_ext.lower() == '.xlsx':
                try:
                    Excel.excel_to_txt_file(file_path, output_file_path)
                    print(f"Saved .txt to: {output_file_path}")
                except Exception as e:
                    print(f"Error extracting data from {file_name}: {e}")
                    continue

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
            continue


if __name__ == "__main__":
    directory_to_process = "/Users/chazzromeo/Desktop/parkcitysoccer"
    # process_files_in_directory(directory_to_process)
