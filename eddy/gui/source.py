from PySide2.QtCore import Signal, QItemSelectionModel
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide2.QtWidgets import QTreeView

from eddy.icons import icons


class SourceModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(SourceModel, self).__init__(parent)

        root = self.invisibleRootItem()

        web_search = QStandardItem(QIcon.fromTheme("globe"), "Web Search")
        web_search.setEditable(False)
        web_search.setSelectable(False)
        local = QStandardItem(QIcon.fromTheme("drive-harddisk"), "Local")
        local.setEditable(False)
        local.setSelectable(False)

        inspire = QStandardItem(QIcon(icons.INSPIRE), "INSPIRE")
        inspire.setEditable(False)
        # inspire_ac = QStandardItem(QIcon(icons.INSPIRE), "ac < 10")
        # inspire_ac.setEditable(False)
        arxiv = QStandardItem(QIcon(icons.ARXIV), "arXiv")
        arxiv.setEditable(False)

        self.ITEMS = {
            "INSPIRE": inspire,
            # "INSPIRE ac": inspire_ac,
            "arXiv": arxiv
        }

        root.appendRow(web_search)
        web_search.appendRow(inspire)
        # inspire.appendRow(inspire_ac)
        web_search.appendRow(arxiv)
        root.appendRow(local)


class SourcePanel(QTreeView):
    SearchRequested = Signal(dict)

    def __init__(self, parent=None):
        super(SourcePanel, self).__init__(parent)

        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        # self.viewport().setAutoFillBackground(False)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

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
        # the value returned by the Sourceal implementation.
        # It might turn out to be useful in the following, where we might not want to
        # automatically respont to any event associated to a selectable index with a Select flag
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

    def SelectSource(self, source):
        item = self.model().ITEMS[source]
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
