import os
import webbrowser
from functools import partial

from PySide2.QtCore import Qt, Signal, QAbstractItemModel, QItemSelectionModel, QModelIndex
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QTreeView, QHeaderView, QMenu

from eddy.icons import icons


class TableModel(QAbstractItemModel):
    SelectionRequested = Signal(QModelIndex)

    HEADERS = (
        "Date",
        "Authors",
        "Title",
        "Citations"
    )
    _KEYS = (
        "date",
        "authors",
        "title",
        "citations"
    )
    _TEXT_ALIGNMENT = {
        "Date": Qt.AlignLeft,
        "Authors": Qt.AlignLeft,
        "Title": Qt.AlignLeft,
        "Citations": Qt.AlignRight
    }

    def __init__(self, parent=None):
        super(TableModel, self).__init__(parent)

        self._table = None
        self._model = []
        self._model_map = []

        self._selected_id = None

        self._sort_key = "id"
        self._sort_order = "ASC"

        self._filter_string = None

    def rowCount(self, parent=QModelIndex()):
        return len(self._model_map)

    def columnCount(self, parent=QModelIndex()):
        return len(TableModel.HEADERS)

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
            return self._model[self._model_map[index.row()]][index.column()]

        if role == Qt.TextAlignmentRole:
            return TableModel._TEXT_ALIGNMENT[TableModel.HEADERS[index.column()]]

        #if role == Qt.ForegroundRole:
        #    return QColor(Qt.red)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return TableModel.HEADERS[section]

        return None

    def sort(self, column, order=Qt.AscendingOrder):
        self._sort_key = TableModel._KEYS[column]
        self._sort_order = "ASC" if order is Qt.AscendingOrder else "DESC"

        if self._model == []:
            return

        self.layoutAboutToBeChanged.emit()
        self._CreateSortFilterMap()
        self.layoutChanged.emit()

        self._RequestSelection()

    def SetTable(self, database_table):
        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)
            self._table.Updated.disconnect(self.Update)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)
        self._table.Updated.connect(self.Update)

    def Clear(self):
        self.beginResetModel()
        self._model = []
        self._model_map = []
        self._selected_id = None
        self.endResetModel()

    def Update(self):
        self.beginResetModel()
        self._model_map = []

        data = self._table.GetTable(TableModel._KEYS)
        self._model = [[
            d["date"],
            TableModel._FormatAuthors(d["authors"]),
            d["title"],
            d["citations"]
        ] for d in data]

        self._CreateSortFilterMap()
        self.endResetModel()

        self._RequestSelection()

    def Filter(self, string):
        if string == "":
            self._filter_string = None
        else:
            self._filter_string = "%" + string + "%"

        if self._model == []:
            return

        self.beginResetModel()
        self._CreateSortFilterMap()
        self.endResetModel()

        self._RequestSelection()

    def SetSelectedRow(self, row):
        if row is None:
            self._selected_id = None
        else:
            self._selected_id = self._model_map[row]

    def IsVisible(self, id_):
        return id_ in self._model_map

    def GetId(self, row):
        return self._model_map[row]

    def GetArXivId(self, row):
        return self._table.GetRecord(self.GetId(row), ("arxiv_id",))["arxiv_id"]

    def GetInspireId(self, row):
        return self._table.GetRecord(self.GetId(row), ("inspire_id",))["inspire_id"]

    def _CreateSortFilterMap(self):
        ids = self._table.GetTable(
            ("id",),
            self._filter_string,
            self._sort_key,
            self._sort_order
        )

        self._model_map = [d["id"] for d in ids]

    def _RequestSelection(self):
        if self._selected_id in self._model_map:
            self.SelectionRequested.emit(self.index(self._model_map.index(self._selected_id), 0))
        else:
            self.SelectionRequested.emit(QModelIndex())

    @staticmethod
    def _FormatAuthors(authors):
        return ", ".join([a.split(",", 1)[0] for a in authors])


class TableView(QTreeView):
    ItemSelected = Signal(int)
    SearchRequested = Signal(str)

    _PERSISTENT_SELECTION_MODE = False

    def __init__(self, parent=None):
        super(TableView, self).__init__(parent)

        self.setItemsExpandable(False)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._HandleRightClickOnItem)


        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self._HandleRightClickOnHeader)
        self.header().setSectionsMovable(False)
        self.header().setStretchLastSection(False)
        self.header().geometriesChanged.connect(self._ResizeColumnsAtGeometryChange)
        self.header().sectionResized.connect(self._ResizeColumnsAtSectionResize)

        self._column_visibility = {}

        self._automatic_selection = False

    def setModel(self, model):
        if self.model() is not None:
            model.SelectionRequested.disconnect(self._HandleSelectionRequested)

        super(TableView, self).setModel(model)

        model.SelectionRequested.connect(self._HandleSelectionRequested)

        self._ResetColumnsSize()
        self._ResizeColumnsAtGeometryChange()

    def reset(self):
        super(TableView, self).reset()

        for h in TableModel.HEADERS:
            if h not in self._column_visibility:
                self._column_visibility[h] = True

        self._SetColumnVisibility()

    def selectionChanged(self, selected, deselected):
        super(TableView, self).selectionChanged(selected, deselected)

        if self._automatic_selection:
            return

        rows = self.selectionModel().selectedRows()
        if rows == []:
            self.model().SetSelectedRow(None)
            self.ItemSelected.emit(-1)
        else:
            row = rows[0].row()
            self.model().SetSelectedRow(row)
            self.ItemSelected.emit(self.model().GetId(row))

    def _HandleRightClickOnHeader(self, position):
        menu = QMenu()

        for h in TableModel.HEADERS:
            a = menu.addAction(h)
            a.setCheckable(True)
            a.setChecked(self._column_visibility[h])
            a.triggered.connect(partial(self._FlipColumnVisibility, h))

        menu.exec_(self.mapToGlobal(position))

    def _HandleRightClickOnItem(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()
        action_inspire_page = menu.addAction(QIcon(icons.INSPIRE), "Open INSPIRE page")
        action_arxiv_page = menu.addAction(QIcon(icons.ARXIV), "Open arXiv page")
        action_arxiv_pdf = menu.addAction(QIcon.fromTheme("viewpdf"), "Open arXiv PDF")
        action_references = menu.addAction(QIcon.fromTheme("system-search"), "Find references")
        action_citations = menu.addAction(QIcon.fromTheme("system-search"), "Find citations")

        arxiv_id = self.model().GetArXivId(index.row())
        if arxiv_id == "":
            action_arxiv_page.setEnabled(False)
            action_arxiv_pdf.setEnabled(False)
        else:
            arxiv_url = "https://arxiv.org/abs/" + arxiv_id
            action_arxiv_page.triggered.connect(partial(self._OpenURL, arxiv_url))
            pdf_url = "https://arxiv.org/pdf/" + arxiv_id + ".pdf"
            action_arxiv_pdf.triggered.connect(partial(self._OpenPDF, pdf_url))

        inspire_id = str(self.model().GetInspireId(index.row()))
        if inspire_id == "":
            action_inspire_page.setEnabled(False)
            action_references.setEnabled(False)
            action_citations.setEnabled(False)
        else:
            inspire_url = "https://labs.inspirehep.net/literature/" + inspire_id
            action_inspire_page.triggered.connect(partial(self._OpenURL, inspire_url))
            ref_string = "citedby:recid:" + inspire_id
            action_references.triggered.connect(partial(self.SearchRequested.emit, ref_string))
            cit_string = "refersto:recid:" + inspire_id
            action_citations.triggered.connect(partial(self.SearchRequested.emit, cit_string))

        menu.exec_(self.viewport().mapToGlobal(position))

    def _HandleSelectionRequested(self, index):
        selection_model = self.selectionModel()
        selection_model.clearCurrentIndex()

        if not index.isValid():
            if not TableView._PERSISTENT_SELECTION_MODE:
                self.model().SetSelectedRow(None)
                self.ItemSelected.emit(-1)
        else:
            self._automatic_selection = True
            selection_model.select(
                index,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            self._automatic_selection = False

    def _SetColumnVisibility(self):
        for (i, h) in enumerate(TableModel.HEADERS):
            self.setColumnHidden(i, not self._column_visibility[h])

    def _FlipColumnVisibility(self, header):
        self._column_visibility[header] = not self._column_visibility[header]
        self.setColumnHidden(TableModel.HEADERS.index(header), not self._column_visibility[header])
        self._ResizeColumnsAtGeometryChange()

    def _ResetColumnsSize(self):
        self.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.header().resizeSection(0, 75)
        self.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.header().resizeSection(1, 250)
        self.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.header().resizeSection(3, 64)

    def _ResizeColumnsAtGeometryChange(self):
        self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.header().sectionSize(2) # Somehow this is necessary
        self.header().setSectionResizeMode(2, QHeaderView.Interactive)

    def _ResizeColumnsAtSectionResize(self, logicalIndex, oldSize, newSize):
        if logicalIndex == 1:
            self.header().resizeSection(2, self.header().sectionSize(2) - newSize + oldSize)

    @staticmethod
    def _OpenPDF(url):
        os.system("okular " + url + " &")

    @staticmethod
    def _OpenURL(url):
        webbrowser.open(url)
