import json
import os
from types import SimpleNamespace

from PySide2.QtCore import Signal, QItemSelectionModel
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide2.QtWidgets import QTreeView, QAbstractItemView

from paths import ROOT_DIR, LOCAL_DATABASES
from eddy.icons import icons
from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import ArXivPlugin
from eddy.data.database import Database, Table


class WebSource:
    def __init__(self, name, plugin, icon, query_map=lambda x: x):
        self.name = name
        self.icon = icon
        self.query_map = query_map
        self.plugin = plugin

    def CreateSearch(self, query):
        query = self.query_map(query)
        return WebSearch(self.icon, query, self.plugin)


# class SearchSource:
#     def __init__(self, name, web_source, query):
#         self.name = name
#         self.web_source = web_source
#         self.query = query


class LocalSource:
    def __init__(self, name, file):
        self.name = name
        self.table = Table(Database(file), "items")


class WebSearch(SimpleNamespace):
    def __init__(self, icon, query, plugin):
        super().__init__(icon=icon, query=query, plugin=plugin)


class SearchRequest(SimpleNamespace):
    # The argument source contains the string associated with a key in SourceModel.WEB_SOURCES
    def __init__(self, source, query):
        super().__init__(source=source, query=query)


class SourceModel(QStandardItemModel):
    WEB_SOURCES = {
        "INSPIRE": WebSource("INSPIRE", InspirePlugin, icons.INSPIRE),
        "arXiv": WebSource("arXiv", ArXivPlugin, icons.ARXIV)
    }

    def __init__(self, parent=None):
        super(SourceModel, self).__init__(parent)

        root = self.invisibleRootItem()

        web_search = QStandardItem(QIcon(icons.WEB), "Web Search")
        web_search.setEditable(False)
        web_search.setSelectable(False)
        web_search.setDropEnabled(False)
        local = QStandardItem(QIcon(icons.LOCAL), "Local")
        local.setEditable(False)
        local.setSelectable(False)
        local.setDropEnabled(False)

        root.appendRow(web_search)
        root.appendRow(local)

        self._ITEMS = {}
        for (n, s) in SourceModel.WEB_SOURCES.items():
            i = QStandardItem(QIcon(s.icon), s.name)
            i.setData(s)
            i.setEditable(False)
            i.setDropEnabled(False)
            self._ITEMS[n] = i
            web_search.appendRow(i)

        for (n, p) in LOCAL_DATABASES.items():
            if not os.path.isfile(p):
                print("Error: Cannot find database file", p)
                continue

            s = LocalSource(n, p)
            i = QStandardItem(QIcon(icons.DATABASE), n)
            i.setData(s)
            i.setEditable(False)
            local.appendRow(i)

    def mimeTypes(self):
        return ["application/x-eddy"]

    def canDropMimeData(self, data, action, row, column, parent):
        # Drop only on valid indices, where parent is the index and row = column = -1
        if (row, column) != (-1, -1):
            return False
        if not parent.isValid():
            return False

        # We should find a way to prevent self-drops.
        # This is difficult since this class does not know about the selected index
        # and provides the model for many view instances.
        # One way out would be to include in the mime data the table where these come from.
        #
        # if self.itemFromIndex(parent).data().table == …:
        #     return False

        return True

    def dropMimeData(self, data, action, row, column, parent):
        records = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))
        self.itemFromIndex(parent).data().table.AddData(records)

        return True


class SourcePanel(QTreeView):
    SearchRequested = Signal(dict)
    WebSourceSelected = Signal()
    LocalSourceSelected = Signal(LocalSource)
    # SourceSelected = Signal((WebSource,), (LocalSource,))

    def __init__(self, parent=None):
        super(SourcePanel, self).__init__(parent)

        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        # self.viewport().setAutoFillBackground(False)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

        self.setDragDropMode(QAbstractItemView.DropOnly)

    def setModel(self, model):
        super(SourcePanel, self).setModel(model)

        self.expandAll()

    def selectionCommand(self, index, event):
        # selection_flags = super(SourcePanel, self).selectionCommand(index, event)

        # NOTE: selectionCommand returns QItemSelectionModel.SelectionFlag
        # Then enum value corresponding to the flag can be accessed with int().
        # In the current setup, two values are produced:
        # Clear | Select | Rows -> 35
        # Deselect | Rows -> 36

        # For the moment, it does not seem to be necessary to read
        # the value returned by the original implementation.
        # It might turn out to be useful in the following, where we might not want to
        # automatically respond to any event associated to a selectable index with a Select flag
        # (e.g. a request for a context menu).

        if not index.isValid():
            return QItemSelectionModel.NoUpdate

        if not self.model().itemFromIndex(index).isSelectable():
            return QItemSelectionModel.NoUpdate

        return QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows

    def selectionChanged(self, selected, deselected):
        super(SourcePanel, self).selectionChanged(selected, deselected)

        rows = self.selectionModel().selectedRows()
        if rows == []:
            return

        source = self.model().itemFromIndex(rows[0]).data()
        if isinstance(source, LocalSource):
            self.LocalSourceSelected.emit(source)
        else:
            self.WebSourceSelected.emit()

    def SelectSource(self, source):
        item = self.model()._ITEMS[source]
        index = self.model().indexFromItem(item)

        selection_model = self.selectionModel()

        rows = selection_model.selectedRows()
        if not rows == []:
            if index == rows[0]:
                return

        selection_model.select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )

    def LaunchSearch(self, query):
        rows = self.selectionModel().selectedRows()
        if len(rows) != 1:
            return

        source = self.model().itemFromIndex(rows[0]).data()

        if isinstance(source, WebSource):
            self.SearchRequested.emit(source.CreateSearch(query))
