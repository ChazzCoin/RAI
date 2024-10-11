from rai.data.RaiFileLoader import RaiFileLoader
from rai.data.RaiWebLoader import RaiWebCrawler

RAI_DBs = lambda db: (f"{db}-main", f"{db}-internal", f"{db}-development")

def delete_collects(*collections):
    RaiFileLoader.delete_collections(*collections)

def import_directory(directory, prefix):
    return RaiFileLoader(directory, prefix).import_directory_into_chroma()

def scrape_site(url:str, pages=0):
    """ pages = 0 -> unlimited"""
    RaiWebCrawler.save('https://textract.readthedocs.io/en/stable/', page_limit=pages)

if __name__ == '__main__':
    db = "parkcitysc"
    delete_collects(*RAI_DBs(db))
    import_directory("/Users/chazzromeo/Desktop/ParkCityTrainingData", db)