from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest
from eddy.network.fetcher import Callback


class DOIBibTeXPlugin():
    @staticmethod
    def Start(search_string):
        # url = "http://doi.org/" + search_string
        url = "https://api.crossref.org/works/" + search_string + "/transform/application/x-bibtex"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/x-bibtex")

        return(None, Callback([], request))

    @staticmethod
    def HandleReply(status, reply_string):
        return (None, Callback([reply_string.replace("\t", "    ")], None))
