from files.open import DataLoader
from F import OS
path = f"{OS.get_path(__file__)}/data"
dataloader = DataLoader(path)

def load_txt_file(file_name):
    return dataloader.load_txt(file_name)

def load_json_file(file_name):
    return dataloader.load_json(file_name)

def load_jsonl_file(file_name):
    return dataloader.load_jsonl(file_name)


# print(load_txt_file("PCSC Player Handbook - Update"))