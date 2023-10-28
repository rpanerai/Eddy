from PySide2.QtCore import QObject, Signal
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkReply


NETWORK_MANAGER = QNetworkAccessManager()

FALLBACK_BATCH_SIZE = 50


def ParseNetworkError(error):
    return str(error).split(".")[-1]


class Callback():
    def __init__(self, data, request):
        self.data = data
        self.request = request


class Fetcher(QObject):
    FetchingStarted = Signal()
    BatchProgress = Signal(int, int)
    BatchReady = Signal(list)
    FetchingFinished = Signal()
    FetchingStopped = Signal()
    FetchingError = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = NETWORK_MANAGER
        self._plugin = None
        self._plugin_status = None
        self._reply = None

    def Stop(self):
        if self._reply is not None:
            self._reply.finished.disconnect()
            self._reply.abort()
            self._reply.deleteLater()
            self._reply = None
            self.FetchingStopped.emit()

    def Fetch(self, plugin, search_string):
        self.Stop()

        self._plugin = plugin

        self.FetchingStarted.emit()
        self._HandlePluginCallback(*self._plugin.Start(search_string))

    def _HandlePluginCallback(self, status, callback):
        if callback.data != []:
            self.BatchReady.emit(callback.data)

        if callback.request == None:
            self._reply = None
            self.FetchingFinished.emit()
            return

        self._plugin_status = status
        self._SendRequest(callback.request)

    def _SendRequest(self, request):
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self.BatchProgress.emit)
        self._reply.finished.connect(self._HandleReply)

    def _HandleReply(self):
        if self._reply.error() == QNetworkReply.NoError:
            reply_string = str(self._reply.readAll(), "utf-8")
            self._reply.deleteLater()

            self._HandlePluginCallback(*self._plugin.HandleReply(self._plugin_status, reply_string))
        else:
            error = ParseNetworkError(self._reply.error())
            self._reply.deleteLater()
            self._reply = None
            self.FetchingError.emit(error)
