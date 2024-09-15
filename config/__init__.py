import os
from dotenv import load_dotenv
load_dotenv()

def env(key, default=None):
    obj = os.getenv(key, default)
    return obj

def default_file_path():
    return env("DATA_FILE_PATH")