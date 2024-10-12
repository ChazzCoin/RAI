from rai.data import RaiPath
from rai.data.extraction.RaiFileExtraction import RaiFileExtractor
from rai.data.extraction.RaiWebExtraction import RaiWebExtractor

RAI_DBs = lambda db: (f"{db}-main", f"{db}-internal", f"{db}-development")

def delete_collects(*collections):
    RaiFileExtractor.delete_collections(*collections)

def import_directory(directory, prefix):
    return RaiFileExtractor(directory, prefix).import_directory_into_chroma()

def scrape_site(url:str, pages=0):
    """ pages = 0 -> entire website"""
    RaiWebExtractor.save(url, page_limit=pages)

if __name__ == '__main__':
    db = "parkone"
    # directory = "/Users/chazzromeo/Desktop/ParkCityTrainingData"
    directory = "/Users/chazzromeo/Desktop/data"
    # training_path = RaiPath.find_directory_path("ParkCityTrainingData")
    # print(training_path)
    # delete_collects(*RAI_DBs(db))
    import_directory(directory, db)