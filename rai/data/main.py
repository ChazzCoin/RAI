from rai.data.extraction.RaiFileExtraction import RaiFileExtractor
from rai.data.extraction.RaiWebExtraction import RaiWebExtractor

RAI_DBs = lambda db: (f"{db}-main", f"{db}-internal", f"{db}-development")

def delete_collects(*collections):
    RaiFileExtractor.delete_collections(*collections)

def import_directory(pipeline, directory, prefix):
    return RaiFileExtractor(pipeline=pipeline, base_directory=directory, collection_prefix=prefix).import_directory()

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
    import_directory("chroma", directory, db)