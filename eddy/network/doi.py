from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class DOIBibTeXPlugin():
    DEFAULT_BATCH_SIZE = 1

    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        # url = "http://doi.org/" + search_string
        url = "https://api.crossref.org/works/" + search_string + "/transform/application/x-bibtex"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/x-bibtex")

        return request

    @staticmethod
    def DecodeBatch(reply_string):
        return ([reply_string.replace("\t", "    ")], 1)
