from urllib.parse import urlparse


def remove_non_printable_ascii(text):
    """
    Remove non-printable characters from text.
    """
    return ''.join([c for c in text if ord(c) < 128])

class RaiUrl(str):
    url: str = ""
    url_obj = None

    def __init__(self, url:str):
        self.url = url
        self.url_obj = urlparse(url)

    def __new__(cls, url):
        # `__new__` is used to create the actual instance since str is immutable
        return super(RaiUrl, cls).__new__(cls, url)
    @property
    def site_name(self):
        return self.url_obj.netloc
    @property
    def savable_name(self, replace_with:str='_'):
        return self.url_obj.netloc.replace('.', replace_with)
    @property
    def path(self):
        return self.url_obj.path  # /some/path
    @property
    def scheme(self):
        return self.url_obj.scheme  # https
    def join_to_base(self, ext):
        return f"{self.url_obj.scheme}://{self.url_obj.netloc}/{ext}"


