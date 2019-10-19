from PySide2.QtCore import QObject, Signal
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkReply


NETWORK_MANAGER = QNetworkAccessManager()


def ParseNetworkError(error):
    return str(error).split(".")[-1]


class Fetcher(QObject):
    FetchingStarted = Signal()
    BatchProgress = Signal(int, int)
    BatchReady = Signal(dict)
    FetchingFinished = Signal(int)
    FetchingStopped = Signal()
    FetchingError = Signal(str)

    def __init__(self, parent=None):
        super(Fetcher, self).__init__(parent)

        self._manager = NETWORK_MANAGER

        self._plugin = None

        self._search_string = None
        self._batch_size = None
        self._page = None
        self._reply = None

    def Fetch(self, plugin, search_string, batch_size):
        self.Stop()

        self._plugin = plugin
        self._batch_size = batch_size
        self._search_string = search_string

        self._page = 1

        self.FetchingStarted.emit()
        self._FetchBatch()

    def Stop(self):
        if self._reply is not None:
            self._reply.finished.disconnect()
            self._reply.abort()
            self._reply.deleteLater()
            self._reply = None
            self.FetchingStopped.emit()

    def _FetchBatch(self):
        request = self._plugin.CreateRequest(self._search_string, self._batch_size, self._page)
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self.BatchProgress.emit)
        self._reply.finished.connect(self._HandleBatch)

    def _HandleBatch(self):
        if self._reply.error() == QNetworkReply.NoError:
            reply_string = str(self._reply.readAll(), "utf-8")
            self._reply.deleteLater()

            base_id = (self._page - 1) * self._batch_size
            (data, total) = self._plugin.DecodeBatch(reply_string, base_id)

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
            error = ParseNetworkError(self._reply.error())
            self._reply.deleteLater()
            self._reply = None
            self.FetchingError.emit(error)
