from functools import partial
import json
from datetime import datetime

try:
    from pylatexenc.latex2text import LatexNodes2Text
    HAS_PYLATEXENC = True
except ImportError:
    HAS_PYLATEXENC = False

from PySide2.QtCore import (
    Qt, Signal, QAbstractItemModel, QItemSelection, QItemSelectionModel, QModelIndex, QMimeData,
    QByteArray
)
from PySide2.QtGui import QIcon, QDrag
from PySide2.QtWidgets import QAbstractItemView, QTreeView, QHeaderView, QMenu, QLabel

from eddy.icons import icons
from eddy.core.web import INSPIRE_SOURCE
from eddy.core.platform import OpenLocalDocument, OpenOnlineDocument, OpenWebURL
from eddy.database.items import SortBy
from eddy.network import inspire, arxiv


class TableData:
    ''' Presents the data in ItemsTable in a convenient way to be consumed by TreeModel.
        NOTE: an TableData object should be discarded every time ItemsTable is updated!
    '''

    _KEYS = (
        "id",
        "date",
        "authors",
        "editors",
        "title",
        "citations"
    )

    def __init__(self, table):
        self._table = table

        self._ids = []      # Maps a row index to the correspoding id
        self._row_map = []  # Maps a row index to the row index in raw_data

        if self._table is None:
            self.raw_data = [[]]
            self._ids_dict = {}
            return

        data = table.GetTable(TableData._KEYS)

        # The unsorted and unfiltered data in _table, with structure
        # [date, authors/editors, title, citations]
        self.raw_data = [[
            d["date"],
            TableData._FormatAuthors(d["authors"] + d["editors"]),
            TableData._FormatTitle(t if (t := d["title"]) is not None else ""),
            d["citations"]
        ] for d in data]

        # Maps an id to the corresponding row index in raw_data
        self._ids_dict = dict((v, i) for i, v in enumerate([d["id"] for d in data]))

    def __len__(self):
        return len(self._row_map)

    def __getitem__(self, position):
        return TableRow(self._row_map[position], self._ids[position], self)

    @property
    def table(self):
        return self._table

    @property
    def ids(self):
        return self._ids

    def SortFilter(self, sort_by, filter_strings, tags):
        if self._table is None:
            return
        self._ids = [d["id"] for d in self.table.GetTable(("id",), sort_by, filter_strings, tags)]
        self._row_map = [self._ids_dict[i] for i in self._ids]

    @staticmethod
    def _FormatAuthors(authors):
        return ", ".join([a.split(",", 1)[0] for a in authors])

    @staticmethod
    def _FormatTitle(text):
        if HAS_PYLATEXENC:
            return LatexNodes2Text().latex_to_text(text)
        return text


class TableRow:
    ''' A row in TableData.
        NOTE: a TableRow object should be used immediately and then discarded!
    '''

    def __init__(self, index, id, table_data):
        self._index = index # The row index in raw_data
        self._id = id
        self._table_data = table_data

    def __len__(self):
        return len(TableModel.HEADERS)

    def __getitem__(self, position):
        return self._table_data.raw_data[self._index][position]

    @property
    def id(self):
        return self._id

    @property
    def record(self):
        return self._table_data.table.GetRow(self._id)

    @property
    def arxiv_id(self):
        return self._table_data.table.GetRow(self._id, ("arxiv_id",))["arxiv_id"]

    @property
    def inspire_id(self):
        return self._table_data.table.GetRow(self._id, ("inspire_id",))["inspire_id"]

    @property
    def dois(self):
        return self._table_data.table.GetRow(self._id, ("dois",))["dois"]

    @property
    def tags(self):
        return self._table_data.table.GetRow(self._id, ("tags",))["tags"]

    @property
    def files(self):
        return self._table_data.table.GetRow(self._id, ("files",))["files"]


class SortTreeBy(SortBy):
    def __init__(self, key, order):
        match order:
            case Qt.AscendingOrder:
                order = SortBy.ASCENDING
            case Qt.DescendingOrder:
                order = SortBy.DESCENDING
        super().__init__(key, order)


class TableModel(QAbstractItemModel):
    NewItemCreated = Signal(QModelIndex)

    HEADERS = (
        "Date",
        "Authors",
        "Title",
        "Cites"
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
        "Cites": Qt.AlignRight
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.source = None
        self._table = None

        self._table_data = TableData(None)

        self._sort_by = SortTreeBy(key="date", order=Qt.DescendingOrder)
        self._filter_strings = []
        self._tags = []

    def __len__(self):
        return len(self._table_data)

    def __getitem__(self, position):
        return self._table_data[position]

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._table_data)

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
        match role:
            case Qt.DisplayRole:
                return self[index.row()][index.column()]
            case Qt.TextAlignmentRole:
                return TableModel._TEXT_ALIGNMENT[TableModel.HEADERS[index.column()]]
            case _:
                return None

    def flags(self, index):
        if not index.isValid():
            return 0
        return Qt.ItemIsDragEnabled | super().flags(index)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return TableModel.HEADERS[section]
        return None

    def sort(self, column, order=Qt.AscendingOrder):
        self._sort_by = SortTreeBy(key=TableModel._KEYS[column], order=order)

        self.layoutAboutToBeChanged.emit()
        self._CreateSortFilterMap()
        self.layoutChanged.emit()

    def mimeTypes(self):
        return ["application/x-eddy", "text/plain"]

    def mimeData(self, indexes):
        rows = [self[r] for r in list({i.row() for i in indexes})]
        ids = [r.id for r in rows]
        records = [r.record for r in rows]
        texkeys = [r["texkey"] for r in records if r["texkey"] is not None]
        file_ = str(self._table.database.file)
        data_list = [file_, ids, records]

        data = QMimeData()
        data.setData(self.mimeTypes()[0], QByteArray(json.dumps(data_list).encode("utf-8")))
        data.setText(", ".join(texkeys))
        return data

    def SetLocalSource(self, source):
        if self.source == source:
            return
        self.source = source
        self._SetTable(source.table)

    def SetTable(self, database_table):
        if self._table == database_table:
            return
        self.source = None
        self._SetTable(database_table)

    def _SetTable(self, database_table):
        self._tags = []

        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)
            self._table.Updated.disconnect(self.Update)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)
        self._table.Updated.connect(self.Update)

        # By first clearing, we empy _selected_ids in the view.
        self.Clear()
        self.Update()

    def SetTags(self, tags):
        self._tags = [t.id for t in tags]
        self._Filter()

    def Clear(self):
        self.beginResetModel()
        self._table_data = TableData(None)
        self.endResetModel()

    def Update(self):
        self.beginResetModel()
        self._table_data = TableData(self._table)
        self._CreateSortFilterMap()
        self.endResetModel()

    def Filter(self, filter_strings):
        self._filter_strings = filter_strings
        self._Filter()

    def _Filter(self):
        self.beginResetModel()
        self._CreateSortFilterMap()
        self.endResetModel()

    def FilterSelection(self, ids):
        return [i for i in ids if i in self._table_data.ids]

    def IndicesFromIds(self, ids):
        return [self.index(self._table_data.ids.index(i), 0) for i in ids]

    def NewItem(self):
        data = {"date": datetime.today().strftime("%Y-%m-%d")}
        if self._tags != []:
            data["tags"] = [self._tags[0]]
        id_ = self._table.AddData([data])
        (index,) = self.IndicesFromIds((id_,))
        self.NewItemCreated.emit(index)

    def DeleteRows(self, rows):
        ids = [r.id for r in rows]
        self._table.Delete(ids)

    def _CreateSortFilterMap(self):
        self._table_data.SortFilter(self._sort_by, self._filter_strings, self._tags)


class TableView(QTreeView):
    ItemSelected = Signal(int)
    NewTabRequested = Signal(dict)
    StatusUpdated = Signal(int, list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setItemsExpandable(False)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._HandleRightClickOnItem)

        self.doubleClicked.connect(self._HandleDoubleClickOnItem)

        self.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self._HandleRightClickOnHeader)
        self.header().setSectionsMovable(False)
        self.header().setStretchLastSection(False)

        self._column_visibility = {h: True for h in TableModel.HEADERS}
        self._show_citations = True

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self._selected_ids = []

        self.setDragDropMode(QAbstractItemView.DragOnly)

    @property
    def _model(self):
        return self.model()

    def setModel(self, model):
        if self._model is not None:
            model.modelAboutToBeReset.disconnect(self._SaveSelection)
            model.layoutAboutToBeChanged.disconnect(self._SaveSelection)
            model.modelReset.disconnect(self._RestoreSelection)
            model.layoutChanged.disconnect(self._RestoreSelection)
            model.NewItemCreated.disconnect(self.setCurrentIndex)

        super().setModel(model)

        model.modelAboutToBeReset.connect(self._SaveSelection)
        model.layoutAboutToBeChanged.connect(self._SaveSelection)
        model.modelReset.connect(self._RestoreSelection)
        model.layoutChanged.connect(self._RestoreSelection)
        model.NewItemCreated.connect(self.setCurrentIndex)

        self._ResetColumnsSize()

    def reset(self):
        super().reset()

        self._SetColumnVisibility()

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)

        ids = [self._model[r.row()].id for r in self.selectionModel().selectedRows()]
        if len(ids) == 1:
            self.ItemSelected.emit(*ids)
        else:
            self.ItemSelected.emit(-1)

        self.StatusUpdated.emit(self._model.rowCount(), ids)

    def startDrag(self, supportedActions):
        # We reimplement this to visualize a tooltip instead of entire rows while dragging.

        rows = self.selectionModel().selectedRows()
        data = self._model.mimeData(rows)

        label = QLabel(f"{len(rows)} items" if len(rows) > 1 else "1 item")
        # Use QPalette.ColorRole?
        label.setStyleSheet(
            "font-weight: bold; color: white; background-color: black; border: 1px solid grey"
        )
        pixmap = label.grab()
        pixmap.rect().adjust(10, 10, 0, 0)

        drag = QDrag(self)
        drag.setPixmap(pixmap)
        # drag.setDragCursor(pixmap, Qt.CopyAction)
        drag.setMimeData(data)
        drag.setHotSpot(pixmap.rect().center())
        drag.exec_(Qt.CopyAction)

    def SetShowCitations(self, show):
        if self._show_citations is not show:
            self._show_citations = show
            self._SetColumnVisibility()

    def _SaveSelection(self):
        self._selected_ids = [
            self._model[r.row()].id for r in self.selectionModel().selectedRows()
        ]

    def _RestoreSelection(self):
        # I have no idea why this does not work if executed at the end of reset(),
        # which, by the way, is triggered by the same signal!

        if self._selected_ids == []:
            self.StatusUpdated.emit(self._model.rowCount(), 0)
            return

        ids = self._model.FilterSelection(self._selected_ids)
        if ids == []:
            self.ItemSelected.emit(-1)
            self.StatusUpdated.emit(self._model.rowCount(), 0)
            return

        indices = self._model.IndicesFromIds(ids)

        selection = QItemSelection()
        for i in indices:
            selection.select(i, i)
        self.selectionModel().select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )

    def _HandleDoubleClickOnItem(self, index):
        if self._model.source is None:
            return []
        dir_ = self._model.source.FilesDir()
        row = self._model[index.row()]
        paths = [dir_ / f for f in row.files]
        for p in paths:
            OpenLocalDocument(p)

    def _HandleRightClickOnHeader(self, position):
        menu = QMenu()
        for h in TableModel.HEADERS:
            if not self._show_citations and h == "Cites":
                continue
            a = menu.addAction(h)
            a.setCheckable(True)
            a.setChecked(self._column_visibility[h])
            a.triggered.connect(partial(self._FlipColumnVisibility, h))
        menu.exec_(self.mapToGlobal(position))

    def _HandleRightClickOnItem(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            if self._model.source is None:
                return
            self.selectionModel().clearSelection()

        rows = [self._model[r.row()] for r in self.selectionModel().selectedRows()]
        menu = self._ContextMenu(rows)
        menu.exec_(self.viewport().mapToGlobal(position))

    def _ContextMenu(self, rows):
        if len(rows) == 0:
            menu = QMenu()
            action_new = menu.addAction(QIcon(icons.ADD), "New item")
            action_new.triggered.connect(self._model.NewItem)
            return menu

        if len(rows) == 1:
            menu = ItemContextMenu(*rows, self._model)
            menu.NewTabRequested.connect(self.NewTabRequested)
            return menu

        menu = QMenu()
        action_delete = menu.addAction(QIcon(icons.DELETE), f"Remove {len(rows)} items")
        action_delete.triggered.connect(partial(self._model.DeleteRows, rows))
        return menu

    def _SetColumnVisibility(self):
        for (i, h) in enumerate(TableModel.HEADERS):
            if not self._show_citations and h == "Cites":
                self.setColumnHidden(i, True)
                continue
            self.setColumnHidden(i, not self._column_visibility[h])

    def _FlipColumnVisibility(self, header):
        self._column_visibility[header] = not self._column_visibility[header]
        self.setColumnHidden(TableModel.HEADERS.index(header), not self._column_visibility[header])

    def _ResetColumnsSize(self):
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.header().resizeSection(1, 250)
        self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)


class ItemContextMenu(QMenu):
    NewTabRequested = Signal(dict)

    def __init__(self, row, table_model, parent=None):
        super().__init__(parent)

        self._AddWebSection(row)
        self.addSeparator()
        if table_model.source is not None:
            self._AddLocalSection(row, table_model)
            self.addSeparator()
        action_delete = self.addAction(QIcon(icons.DELETE), "Remove")
        action_delete.triggered.connect(partial(table_model.DeleteRows, (row,)))

    @staticmethod
    def _FilesMenu(row, table_model):
        if (files := row.files) == []:
            return None
        dir_ = table_model.source.FilesDir()

        menu = QMenu()
        for f in files:
            a = menu.addAction(icons.FileIcon(f), f)
            a.triggered.connect(partial(OpenLocalDocument, dir_ / f))
        return menu

    @staticmethod
    def _TagsMenu(row, table_model):
        tags = row.tags
        if tags == []:
            return None

        menu = QMenu()
        for t in tags:
            a = menu.addAction(QIcon(icons.TAG), table_model.source.TagMap()[t])
            a.triggered.connect(partial(table_model.source.DropTagFromItem, row.id, t))
        return menu

    def _AddWebSection(self, row):
        action_inspire_page = self.addAction(QIcon(icons.INSPIRE), "Open INSPIRE page")
        action_arxiv_page = self.addAction(QIcon(icons.ARXIV), "Open arXiv page")
        action_arxiv_pdf = self.addAction(QIcon(icons.PDF), "Open arXiv PDF")
        action_doi_link = self.addAction(QIcon(icons.DOI), "Open DOI links")
        self.addSeparator()
        action_references = self.addAction(QIcon(icons.SEARCH), "Find references")
        action_citations = self.addAction(QIcon(icons.SEARCH), "Find citations")

        if (arxiv_id := row.arxiv_id) is None:
            action_arxiv_page.setEnabled(False)
            action_arxiv_pdf.setEnabled(False)
        else:
            arxiv_url = arxiv.AbstractUrl(arxiv_id)
            action_arxiv_page.triggered.connect(partial(OpenWebURL, arxiv_url))
            pdf_url = arxiv.PDFUrl(arxiv_id)
            action_arxiv_pdf.triggered.connect(partial(OpenOnlineDocument, pdf_url))

        if (inspire_id := row.inspire_id) is None:
            action_inspire_page.setEnabled(False)
            action_references.setEnabled(False)
            action_citations.setEnabled(False)
        else:
            inspire_url = inspire.LiteratureUrl(inspire_id)
            action_inspire_page.triggered.connect(partial(OpenWebURL, inspire_url))
            ref_search = INSPIRE_SOURCE.CreateSearch(f"citedby:recid:{inspire_id}")
            action_references.triggered.connect(partial(self.NewTabRequested.emit, ref_search))
            cit_search = INSPIRE_SOURCE.CreateSearch(f"refersto:recid:{inspire_id}")
            action_citations.triggered.connect(partial(self.NewTabRequested.emit, cit_search))

        if (dois := row.dois) == []:
            action_doi_link.setEnabled(False)
        else:
            doi_urls = (f"https://doi.org/{s}" for s in dois)
            for u in doi_urls:
                action_doi_link.triggered.connect(partial(OpenWebURL, u))

    def _AddLocalSection(self, row, table_model):
        files_menu = ItemContextMenu._FilesMenu(row, table_model)
        if files_menu is None:
            action_files = self.addAction(QIcon(icons.FILES), "Open files")
            action_files.setEnabled(False)
        else:
            action_files = self.addMenu(files_menu)
            action_files.setIcon(QIcon(icons.FILES))
            action_files.setText("Open files")
        self.addSeparator()
        tags_menu = ItemContextMenu._TagsMenu(row, table_model)
        if tags_menu is None:
            action_tags = self.addAction(QIcon(icons.STOP), "Drop tags")
            action_tags.setEnabled(False)
        else:
            action_tags = self.addMenu(tags_menu)
            action_tags.setIcon(QIcon(icons.STOP))
            action_tags.setText("Drop tags")
        self.addSeparator()
        action_new = self.addAction(QIcon(icons.ADD), "New item")
        action_new.triggered.connect(table_model.NewItem)
