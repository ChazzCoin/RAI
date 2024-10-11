from rai.data.RaiFileLoader import RaiFileLoader


def import_directory(directory, prefix):
    return RaiFileLoader(directory, prefix).import_directory_into_chroma()


if __name__ == '__main__':
    db = "parkcitysc"
    RaiFileLoader.delete_collections(f"{db}-main", f"{db}-internal", f"{db}-development")
    import_directory("/Users/chazzromeo/Desktop/ParkCityTrainingData", db)