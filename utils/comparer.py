import os
import re

def check_require_in_files(directory):
    """
    Check all files in a directory and its subdirectories for the presence of "= require(" string.

    Parameters:
    - directory (str): Path to the directory.

    Returns:
    - failed_files (list of str): List of file paths that did not contain the "= require(" string.
    """
    failed_files = []
    require_regex = r"require\("

    for root, _, files in os.walk(directory):
        print(f"Looking in directory: [ {root} ]")
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.js'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    if not re.search(require_regex, file_content):
                        failed_files.append(file_path)

    return failed_files
def compare_directories(dir1, dir2):
    """
    Compare files in two directories and their subdirectories for the presence of "module.exports =" string.
    Only files with identical names in both directories are compared.

    Parameters:
    - dir1 (str): Path to the first directory.
    - dir2 (str): Path to the second directory.

    Returns:
    - success_count (int): Number of files where both files contain "module.exports =" string.
    - failed_files (list of tuple): List of tuples with the paths of files that did not match the criteria.
    """
    def build_file_dict(directory):
        file_dict = {}
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if file not in file_dict:
                    file_dict[file] = []
                file_dict[file].append(file_path)
        return file_dict

    dir1_files = build_file_dict(dir1)
    dir2_files = build_file_dict(dir2)

    success_count = 0
    failed_files = []

    for file_name in dir1_files:
        if file_name in dir2_files:
            for file1_path in dir1_files[file_name]:
                for file2_path in dir2_files[file_name]:
                    with open(file1_path, 'r', encoding='utf-8') as file1, open(file2_path, 'r', encoding='utf-8') as file2:
                        file1_content = file1.read()
                        file2_content = file2.read()

                        module_exports_regex = r"module\.exports"

                        if re.search(module_exports_regex, file1_content) and re.search(module_exports_regex, file2_content):
                            success_count += 1
                        else:
                            failed_files.append((file1_path, file2_path))
        else:
            for file1_path in dir1_files[file_name]:
                failed_files.append((file1_path, "File not found in dir2"))

    for file_name in dir2_files:
        if file_name not in dir1_files:
            for file2_path in dir2_files[file_name]:
                failed_files.append(("File not found in dir1", file2_path))

    return success_count, failed_files
# Example usage

sub_directory = "helpers"

dir1 = f'/Users/chazzromeo/OneCall/relayhealthcare-webapp-newest/{sub_directory}'
dir2 = f'/Users/chazzromeo/OneCall/relayhealthcare-webapp-newest-copy/{sub_directory}'

# Validater
# failed_files = check_require_in_files(dir1)
# if failed_files:
#     print("Failed files:")
#     for file1 in failed_files:
#         print(f"{file1}")
# Compare
success_count, failed_files = compare_directories(dir1, dir2)
print(f"Success count: {success_count}")
if failed_files:
    print("Failed files:")
    for file1, file2 in failed_files:
        print(f"{file1} <-> {file2}")
