import os
import shutil
import stat

from F.LOG import Log
from langchain_core.document_loaders import BaseLoader
Log = Log("VerifyLoaderData")


def verify_loader_data(loader: BaseLoader) -> bool:
    try:
        # Attempt to load data from the provided loader
        data = loader.load()
        # Check if data is not None, is a list, and has valid contents
        if data is None:
            return False
        if not isinstance(data, list):
            return False
        if len(data) == 0:
            return False
        # If all checks pass, return True
        return True
    except Exception as e:
        # If any exception occurs, log it if needed and return False
        # You could add logging here for better traceability in production
        Log.w("Failed Loader Validation", e)
        return False


def delete_folder(folder_path):
    """
    Deletes a folder and all its contents.

    Parameters:
    - folder_path (str): The path to the folder to delete.

    Raises:
    - FileNotFoundError: If the folder does not exist.
    - NotADirectoryError: If the specified path is not a directory.
    - PermissionError: If the operation lacks the necessary permissions.
    - OSError: For other OS-related errors.
    """

    # You can configure logging to output to a file or console as needed

    # Verify that the path exists
    if not os.path.exists(folder_path):
        Log.e(f"Folder not found: {folder_path}")
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    # Verify that the path is a directory
    if not os.path.isdir(folder_path):
        Log.e(f"Specified path is not a directory: {folder_path}")
        raise NotADirectoryError(f"Specified path is not a directory: {folder_path}")

    # Handle read-only files on Windows
    def onerror(func, path, exc_info):
        """
        Error handler for shutil.rmtree.

        If the error is due to an access error (read-only file), it attempts to add write permission and retries.
        If the error is for another reason, it re-raises the error.
        """
        if not os.access(path, os.W_OK):
            # Attempt to add write permission
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise

    try:
        shutil.rmtree(folder_path, onerror=onerror)
        Log.i(f"Successfully deleted folder and its contents: {folder_path}")
    except Exception as e:
        Log.e(f"Error deleting folder {folder_path}: {e}")
        raise
