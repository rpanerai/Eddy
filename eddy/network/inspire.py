import json
import urllib.parse

from PySide2.QtCore import QObject, Signal, QUrl
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


NETWORK_MANAGER = QNetworkAccessManager()


class InspireFetcher(QObject):
    FetchingStarted = Signal()
    BatchProgress = Signal(int, int)
    BatchReady = Signal(dict)
    FetchingFinished = Signal(int)
    FetchingStopped = Signal()

    _BASE_URL = "https://labs.inspirehep.net/api/literature?sort=mostrecent"

    def __init__(self, parent=None):
        super(InspireFetcher, self).__init__(parent)

        self._manager = NETWORK_MANAGER

        self._url = None
        self._batch_size = None
        self._page = None
        self._reply = None

    def Fetch(self, search_string, batch_size):
        self._batch_size = batch_size
        self._url = (
            InspireFetcher._BASE_URL
            + "&q=" + urllib.parse.quote(search_string)
            + "&size=" + str(self._batch_size)
        )

        self._page = 1

        self.FetchingStarted.emit()
        self._FetchBatch()

    def _FetchBatch(self):
        request = QNetworkRequest(QUrl(self._url + "&page=" + str(self._page)))
        request.setRawHeader(b"Accept", b"application/json")
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self._DownloadProgress)
        self._reply.finished.connect(self._HandleBatch)

    def _HandleBatch(self):
        if self._reply.error() == QNetworkReply.NoError:
            reply_string = str(self._reply.readAll(), "utf-8")
            self._reply.deleteLater()

            (data, total) = self._DecodeBatch(json.loads(reply_string))

            records_found = len(data)
            if records_found > 0:
                self.BatchReady.emit(data)

            if (self._batch_size is not None) and (self._page * self._batch_size < total):
                self._page = self._page + 1
                self._FetchBatch()
            else:
                self._reply = None
                self.FetchingFinished.emit(total)
        else:
            # Here do something to notify the error. Possibly emit a signal or raise an exception.
            print(self._reply.error())
            self._reply.deleteLater()
            self._reply = None

    def _DecodeBatch(self, raw_data):
        base_id = (self._page - 1) * self._batch_size
        data = [{
            "id": i + base_id,
            "type": (
                InspireFetcher._TYPES.get(d["metadata"]["document_type"][0], "")
                if "document_type" in d["metadata"]
                else ""
            ),
            # "date": d["metadata"]["legacy_creation_date"],
            "date": d["metadata"]["earliest_date"],
            "authors": [
                a["full_name"]
                for a in d["metadata"]["authors"]
            ] if "authors" in d["metadata"] else [],
            "title": d["metadata"]["titles"][0]["title"],
            "abstract": (
                d["metadata"]["abstracts"][0]["value"]
                if "abstracts" in d["metadata"]
                else ""
            ),
            "citations": d["metadata"]["citation_count"],
            "journal" : (
                InspireFetcher._DecodeJournal(
                    d["metadata"]["publication_info"][0]
                )
                if "publication_info" in d["metadata"]
                else ""
            ),
            "inspire_id": d["id"],
            "texkey": (
                d["metadata"]["texkeys"][0]
                if "texkeys" in d["metadata"]
                else ""
            ),
            "arxiv_id": (
                d["metadata"]["arxiv_eprints"][0]["value"]
                if "arxiv_eprints" in d["metadata"]
                else ""
            ),
            "dois": list({
                i["value"]
                for i in d["metadata"]["dois"]
            }) if "dois" in d["metadata"] else []
        } for (i, d) in enumerate(raw_data["hits"]["hits"])]

        total = raw_data["hits"]["total"]

        return (data, total)

    def _DownloadProgress(self, bytes_received, bytes_total):
        self.BatchProgress.emit(bytes_received, bytes_total)

    def Stop(self):
        if self._reply is not None:
            self._reply.finished.disconnect()
            self._reply.abort()
            self._reply.deleteLater()
            self._reply = None
            self.FetchingStopped.emit()

    _TYPES = {
        "article": "A",
        "book": "B",
        "book chapter": "C",
        "note": "N",
        "conference paper": "P",
        "proceedings": "P",
        "report": "R",
        "activity report": "R",
        "thesis": "T"
    }

    @staticmethod
    def _DecodeJournal(pub_info):
        if "journal_title" in pub_info:
            text = pub_info["journal_title"]
            if "journal_volume" in pub_info:
                text = text + " " + pub_info["journal_volume"]
            if "year" in pub_info:
                text = text + " (" + str(pub_info["year"]) + ")"
            if "journal_issue" in pub_info:
                text = text + " " + pub_info["journal_issue"]
            if "artid" in pub_info:
                text = text + " " + pub_info["artid"]
            return text

        if "pubinfo_freetext" in pub_info:
            return pub_info["pubinfo_freetext"]

        return ""
