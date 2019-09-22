from PySide2.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide2.QtWidgets import QAbstractItemView, QTableView, QHeaderView


class ItemModel(QAbstractItemModel):
    _FIELDS = {
        "type": "Type",
        "title": "Title",
        "authors": "Authors",
        "abstract": "Abstract",
        "journal": "Journal",
        "texkey": "BibTeX",
        "inspire_id": "INSPIRE",
        "arxiv_id": "arXiv",
        "dois": "DOIs"
    }

    _KEYS = tuple(_FIELDS.keys())

    _HEADERS = tuple(_FIELDS.values()) 

    _FORMAT_TYPE = {
        "A": "Article",
        "P": "Conference Proceedings",
        "T": "Thesis",
        "B": "Book",
        "C": "Book Chapter",
        "N": "Note"
    }

    _FORMAT_FUNCTIONS = {
        "type": lambda x: ItemModel._FORMAT_TYPE.get(x, ""),
        "authors": "\n".join,
        # Alternatively one could use
        # lambda x: "\n".join([a.split(",", 1)[0] for a in x])
        "dois": "\n".join,
    }

    def __init__(self, parent=None):
        super(ItemModel, self).__init__(parent)

        self._table = None

        self._model = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._model)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self._model[index.row()]

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Orientation.Vertical:
            if role == Qt.DisplayRole:
                return ItemModel._HEADERS[section]
            if role == Qt.TextAlignmentRole:
                return Qt.AlignRight

        return None

    # def flags(self, index):
    #     if not index.isValid():
    #         return None

    #     return Qt.ItemIsEnabled

    def SetTable(self, database_table):
        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)

    def Clear(self):
        self.beginResetModel()
        self._model = []
        self.endResetModel()

    def DisplayRecord(self, id_):
        self.beginResetModel()

        if id_ == -1:
            self.Clear()
        else:
            record = self._table.GetRecord(id_, ItemModel._KEYS)

            for k in ItemModel._FORMAT_FUNCTIONS:
                record[k] = ItemModel._FORMAT_FUNCTIONS[k](record[k])

            self._model = list(record.values())

        self.endResetModel()


class ItemView(QTableView):
    def __init__(self, parent=None):
        super(ItemView, self).__init__(parent)

        # self.setShowGrid(False)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().hide()

        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.setSelectionMode(QAbstractItemView.NoSelection)

    def setModel(self, model):
        if self.model() is not None:
            model.modelReset.disconnect(self.expandAll)

        super(ItemView, self).setModel(model)

    def resizeEvent(self, event):
        super(ItemView, self).resizeEvent(event)

        self.resizeRowsToContents()
