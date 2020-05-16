import os
import webbrowser
from functools import partial
import json

from PySide2.QtCore import (
    Qt, Signal, QAbstractItemModel, QItemSelection, QItemSelectionModel, QModelIndex, QMimeData,
    QByteArray
)
from PySide2.QtGui import QIcon, QDrag
from PySide2.QtWidgets import QAbstractItemView, QTreeView, QHeaderView, QMenu, QLabel

from eddy.icons import icons
from eddy.gui.source import SearchRequest


class TableModel(QAbstractItemModel):
    SelectionRequested = Signal(list)

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
        self._ids = []
        self._ids_dict = {}
        self._model_map = []

        self._sort_key = "id"
        self._sort_order = "ASC"

        self._filter_strings = []

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._model_map)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
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

        return None

    def flags(self, index):
        if not index.isValid():
            return 0

        return Qt.ItemIsDragEnabled | super(TableModel, self).flags(index)

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

    def mimeTypes(self):
        return ["application/x-eddy"]

    def mimeData(self, indexes):
        ids = [self._ids[r] for r in list({i.row() for i in indexes})]
        records = [self._table.GetRow(i) for i in ids]

        data = QMimeData()
        data.setData(self.mimeTypes()[0], QByteArray(json.dumps(records).encode("utf-8")))
        return data

    def SetTable(self, database_table):
        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)
            self._table.Updated.disconnect(self.Update)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)
        self._table.Updated.connect(self.Update)

        self.Clear()
        self.Update()

    def Clear(self):
        self.beginResetModel()
        self._model = []
        self._ids = []
        self._ids_dict = {}
        self._model_map = []
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

        ids = self._table.GetTable(("id",))
        self._ids_dict = dict((v, i) for i, v in enumerate([d["id"] for d in ids]))

        self._CreateSortFilterMap()
        self.endResetModel()

    def Filter(self, filter_strings):
        self._filter_strings = filter_strings

        if self._model == []:
            return

        self.beginResetModel()
        self._CreateSortFilterMap()
        self.endResetModel()

    def IsVisible(self, id_):
        return id_ in self._model_map

    def GetId(self, row):
        return self._ids[row]

    def GetArXivId(self, row):
        return self._table.GetRow(self.GetId(row), ("arxiv_id",))["arxiv_id"]

    def GetInspireId(self, row):
        return self._table.GetRow(self.GetId(row), ("inspire_id",))["inspire_id"]

    def GetDOIs(self, row):
        return self._table.GetRow(self.GetId(row), ("dois",))["dois"]

    def FilterSelection(self, ids):
        return [i for i in ids if i in self._ids]

    def IndicesFromIds(self, ids):
        return [self.index(self._ids.index(i), 0) for i in ids]

    def DeleteRows(self, rows):
        ids = [self._ids[r] for r in rows]
        self._table.Delete(ids)

    def _CreateSortFilterMap(self):
        ids = self._table.GetTable(
            ("id",),
            self._sort_key,
            self._sort_order,
            self._filter_strings
        )
        self._ids = [d["id"] for d in ids]
        self._model_map = [self._ids_dict[i] for i in self._ids]

    @staticmethod
    def _FormatAuthors(authors):
        return ", ".join([a.split(",", 1)[0] for a in authors])


class TableView(QTreeView):
    ItemSelected = Signal(int)
    NewTabRequested = Signal(dict)

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

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self._selected_ids = []

        self.setDragDropMode(QAbstractItemView.DragOnly)

    def setModel(self, model):
        if self.model() is not None:
            model.modelAboutToBeReset.disconnect(self._SaveSelection)
            model.modelReset.disconnect(self._RestoreSelection)

        super(TableView, self).setModel(model)

        model.modelAboutToBeReset.connect(self._SaveSelection)
        model.modelReset.connect(self._RestoreSelection)

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

        rows = [r.row() for r in self.selectionModel().selectedRows()]
        if len(rows) == 1:
            self.ItemSelected.emit(self.model().GetId(rows[0]))
        else:
            self.ItemSelected.emit(-1)

    def startDrag(self, supportedActions):
        # We reimplement this to visualize a tooltip instead of entire rows while dragging.
        
        rows = self.selectionModel().selectedRows()
        data = self.model().mimeData(rows)

        label = QLabel(str(len(rows)) + " items" if len(rows) > 1 else "1 item")
        # Use QPalette.ColorRole?
        label.setStyleSheet(
            "font-weight: bold; color : white; background-color : black; border: 1px solid grey"
        )
        pixmap = label.grab()
        pixmap.rect().adjust(10,10,0,0)
        
        drag = QDrag(self)
        drag.setPixmap(pixmap)
        # drag.setDragCursor(pixmap, Qt.CopyAction)
        drag.setMimeData(data)
        drag.setHotSpot(pixmap.rect().center())
        drag.exec_(Qt.CopyAction)

    def _SaveSelection(self):
        self._selected_ids = [
            self.model().GetId(r.row()) for r in self.selectionModel().selectedRows()
        ]

    def _RestoreSelection(self):
        # I have no idea why this does not work if executed at the end of reset(),
        # which, by the way, is triggered by the same signal!

        if self._selected_ids == []:
            return

        ids = self.model().FilterSelection(self._selected_ids)
        if ids == []:
            self.ItemSelected.emit(-1)
            return

        indices = self.model().IndicesFromIds(ids)

        selection = QItemSelection()
        for i in indices:
            selection.select(i, i)
        self.selectionModel().select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )

    def _HandleRightClickOnHeader(self, position):
        menu = QMenu()

        for h in TableModel.HEADERS:
            a = menu.addAction(h)
            a.setCheckable(True)
            a.setChecked(self._column_visibility[h])
            a.triggered.connect(partial(self._FlipColumnVisibility, h))

        menu.exec_(self.mapToGlobal(position))

    def _HandleRightClickOnItem(self, position):
        # index = self.indexAt(position)
        # if not index.isValid():
        #     return
        # row = index.row()

        rows = [r.row() for r in self.selectionModel().selectedRows()]
        if rows == []:
            return

        menu = self._ContextMenu(rows)
        menu.exec_(self.viewport().mapToGlobal(position))

    def _ContextMenu(self, rows):
        menu = QMenu()

        if len(rows) > 1:
            action_delete = menu.addAction(
                QIcon(icons.DELETE),
                "Remove " + str(len(rows)) + " items"
            )
            action_delete.triggered.connect(partial(self.model().DeleteRows, rows))
            return menu

        row = rows[0]

        action_inspire_page = menu.addAction(QIcon(icons.INSPIRE), "Open INSPIRE page")
        action_arxiv_page = menu.addAction(QIcon(icons.ARXIV), "Open arXiv page")
        action_arxiv_pdf = menu.addAction(QIcon(icons.PDF), "Open arXiv PDF")
        action_doi_link = menu.addAction(QIcon(icons.DOI), "Open DOI links")
        menu.addSeparator()
        action_references = menu.addAction(QIcon(icons.SEARCH), "Find references")
        action_citations = menu.addAction(QIcon(icons.SEARCH), "Find citations")
        menu.addSeparator()
        action_delete = menu.addAction(QIcon(icons.DELETE), "Remove")

        arxiv_id = self.model().GetArXivId(row)
        if arxiv_id == None:
            action_arxiv_page.setEnabled(False)
            action_arxiv_pdf.setEnabled(False)
        else:
            arxiv_url = "https://arxiv.org/abs/" + arxiv_id
            action_arxiv_page.triggered.connect(partial(self._OpenURL, arxiv_url))
            pdf_url = "https://arxiv.org/pdf/" + arxiv_id + ".pdf"
            action_arxiv_pdf.triggered.connect(partial(self._OpenPDF, pdf_url))

        inspire_id = self.model().GetInspireId(row)
        if inspire_id == None:
            action_inspire_page.setEnabled(False)
            action_references.setEnabled(False)
            action_citations.setEnabled(False)
        else:
            inspire_id = str(inspire_id)

            inspire_url = "https://labs.inspirehep.net/literature/" + inspire_id
            action_inspire_page.triggered.connect(partial(self._OpenURL, inspire_url))

            ref_search = SearchRequest(source="INSPIRE", query="citedby:recid:" + inspire_id)
            action_references.triggered.connect(partial(self.NewTabRequested.emit, ref_search))

            cit_search = SearchRequest(source="INSPIRE", query="refersto:recid:" + inspire_id)
            action_citations.triggered.connect(partial(self.NewTabRequested.emit, cit_search))

        dois = self.model().GetDOIs(row)
        if dois == []:
            action_doi_link.setEnabled(False)
        else:
            doi_urls = ("https://doi.org/" + s for s in dois)
            for u in doi_urls:
                action_doi_link.triggered.connect(partial(self._OpenURL, u))

        action_delete.triggered.connect(partial(self.model().DeleteRows, (row,)))

        return menu

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
