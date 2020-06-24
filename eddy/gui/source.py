from functools import partial
import json
import os
from types import SimpleNamespace
import shutil

from PySide2.QtCore import Qt, Signal, QItemSelectionModel, QUrl
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem, QDesktopServices
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QMenu, QMessageBox

from paths import ROOT_DIR, STORAGE_FOLDER, LOCAL_DATABASES
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
        self.database = Database(file)
        self.table = Table(self.database, "items")


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
        local = QStandardItem(QIcon(icons.LOCAL), "Local")
        local.setEditable(False)
        local.setSelectable(False)

        root.appendRow(web_search)
        root.appendRow(local)

        self.ITEMS = {}
        for (n, s) in SourceModel.WEB_SOURCES.items():
            i = QStandardItem(QIcon(s.icon), s.name)
            i.setData(s)
            i.setEditable(False)
            self.ITEMS[n] = i
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
        # Drop only on valid indices, where parent is the index and row = column = -1.
        if (row, column) != (-1, -1):
            return False
        if not parent.isValid():
            return False

        target = self.itemFromIndex(parent).data()
        if not isinstance(target, LocalSource):
            return False

        # Prevent drops when origin and target databases coincide
        origin_file = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))[0]
        if target.database.file == origin_file:
            return False

        return True

    def dropMimeData(self, data, action, row, column, parent):
        (origin_file, _, records) = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))

        # In copying items, we drop their citations and tags fields.
        for d in records:
            d.pop("citations")
            d.pop("tags")

        if origin_file == ":memory:":
            self.itemFromIndex(parent).data().table.AddData(records)
            return True

        files = []
        for d in records:
            files = files + d["files"]
        files = set(files)
        if len(files) == 0:
            self.itemFromIndex(parent).data().table.AddData(records)
            return True

        target_file = self.itemFromIndex(parent).data().database.file
        origin_dir = os.path.join(os.path.dirname(os.path.realpath(origin_file)), STORAGE_FOLDER)
        target_dir = os.path.join(os.path.dirname(os.path.realpath(target_file)), STORAGE_FOLDER)
        if target_dir == origin_dir:
            self.itemFromIndex(parent).data().table.AddData(records)
            return True

        if not os.path.isdir(target_dir):
            try:
                os.mkdir(target_dir)
            except:
                QMessageBox.critical(
                    None,
                    "Error",
                    "Cannot access storage folder. Drop action aborted."
                )
                return False

        # Rename files if a file with the same name already exists in the target folder
        copies = []
        renamings = {}
        for f in files:
            file_path = os.path.join(origin_dir, f)
            new_path = os.path.join(target_dir, f)
            i = 1
            while os.path.exists(new_path):
                i = i + 1
                (body, ext) = os.path.splitext(new_path)
                new_path = body + "(" + str(i) + ")" + ext
            copies.append((file_path, new_path))
            if i > 1:
                renamings[f] = os.path.basename(new_path)
        for r in records:
            r["files"] = [renamings.get(f, f) for f in r["files"]]

        for c in copies:
            try:
                shutil.copy2(*c)
            except:
                QMessageBox.critical(
                    None,
                    "Error",
                    "Error while copying '" + c[0] + "'. Drop action aborted."
                )
                return False

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

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._HandleRightClickOnItem)

    def setModel(self, model):
        super(SourcePanel, self).setModel(model)

        self.expandAll()

    def mousePressEvent(self, event):
        # We reimplement this to prevent right clicks from selecting sources
        if event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.selectionModel().setCurrentIndex(index, QItemSelectionModel.Current)
        else:
            super(SourcePanel, self).mousePressEvent(event)

    def selectionCommand(self, index, event):
        # selection_flags = super(SourcePanel, self).selectionCommand(index, event)

        # NOTE: selectionCommand returns QItemSelectionModel.SelectionFlag
        # Then enum value corresponding to the flag can be accessed with int().
        # In the current setup, two values are produced:
        # Clear | Select | Rows -> 35
        # Deselect | Rows -> 36

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
        rows = self.selectionModel().selectedRows()
        if len(rows) != 1:
            return

        source = self.model().itemFromIndex(rows[0]).data()

        if isinstance(source, WebSource):
            self.SearchRequested.emit(source.CreateSearch(query))

    def _HandleRightClickOnItem(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        source = self.model().itemFromIndex(index).data()

        if isinstance(source, LocalSource):
            menu = self._ContextMenuLocalSource(source)
            menu.exec_(self.viewport().mapToGlobal(position))

    def _ContextMenuLocalSource(self, source):
        menu = QMenu()

        action_open = menu.addAction(QIcon(icons.OPEN), "Open folder")

        path = os.path.dirname(source.database.file)
        action_open.triggered.connect(partial(self._OpenPath, path))

        return menu

    @staticmethod
    def _OpenPath(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
