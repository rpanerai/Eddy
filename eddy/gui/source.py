import json

from PySide2.QtCore import Signal, QItemSelectionModel
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide2.QtWidgets import QTreeView, QAbstractItemView

from paths import ROOT_DIR, LOCAL_DATABASES
from eddy.icons import icons
from eddy.data.database import Database, Table


class SourceModel(QStandardItemModel):
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

        inspire = QStandardItem(QIcon(icons.INSPIRE), "INSPIRE")
        inspire.setEditable(False)
        inspire.setDropEnabled(False)
        # inspire_ac = QStandardItem(QIcon(icons.INSPIRE), "ac < 10")
        # inspire_ac.setEditable(False)
        # inspire_ac.setDropEnabled(False)
        arxiv = QStandardItem(QIcon(icons.ARXIV), "arXiv")
        arxiv.setEditable(False)
        arxiv.setDropEnabled(False)

        self._ITEMS = {
            "INSPIRE": inspire,
            # "INSPIRE ac": inspire_ac,
            "arXiv": arxiv
        }

        self._TABLES = {}
        for (n, p) in LOCAL_DATABASES.items():
            self._TABLES[n] = Table(Database(p), "tab")
            i = QStandardItem(QIcon(icons.DATABASE), n)
            i.setEditable(False)
            local.appendRow(i)

        root.appendRow(web_search)
        web_search.appendRow(inspire)
        # inspire.appendRow(inspire_ac)
        web_search.appendRow(arxiv)
        root.appendRow(local)

    def mimeTypes(self):
        return ["application/x-eddy"]

    def canDropMimeData(self, data, action, row, column, parent):
        # We could implement additional logic to prevent self-drops.

        if (row, column) != (-1, -1):
            return False
        if not parent.isValid():
            return False
        # Drop only on valid indices, where parent is the index and row = column = -1.
        return True

    def dropMimeData(self, data, action, row, column, parent):
        self.itemFromIndex(parent)
        table = self._TABLES[self.itemFromIndex(parent).text()]

        records = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))
        table.AddData(records)

        return True


class SourcePanel(QTreeView):
    SearchRequested = Signal(dict)
    WebSourceSelected = Signal()
    LocalSourceSelected = Signal(Table)

    def __init__(self, parent=None):
        super(SourcePanel, self).__init__(parent)

        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        # self.viewport().setAutoFillBackground(False)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

        self.setDragDropMode(QAbstractItemView.DropOnly)

        self._selected_source = None

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

        item = self.model().itemFromIndex(rows[0])
        self._selected_source = item.text()

        table = self.model()._TABLES.get(self._selected_source, None)
        if table == None:
            self.WebSourceSelected.emit()
        else:
            self.LocalSourceSelected.emit(table)

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
        self.SearchRequested.emit({"source": self._selected_source, "query": query})
