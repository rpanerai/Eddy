from functools import partial
import json
import os
from types import SimpleNamespace
import shutil

from PySide2.QtCore import Qt, Signal, QItemSelectionModel, QUrl
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem, QDesktopServices
from PySide2.QtWidgets import (
    QTreeView, QAbstractItemView, QAbstractItemDelegate, QStyledItemDelegate, QMenu, QMessageBox
)

from paths import ROOT_DIR, STORAGE_FOLDER, LOCAL_DATABASES
from eddy.icons import icons
from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import ArXivPlugin
from eddy.data.database import Database
from eddy.data.items import ItemsTable
from eddy.data.tags import TagsTable


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
        self.table = ItemsTable(self.database)
        self.tags_table = TagsTable(self.database)


class Tag:
    def __init__(self, source, id_, name, parent):
        self.source = source
        self.id = id_
        self.name = name
        self.parent = parent

    def Rename(self, name):
        self.source.tags_table.EditRow(self.id, {"name": name})
        self.name = name

    def Delete(self):
        Tag._DeleteIdAndChildren(self.source, self.id)

    @classmethod
    def CreateFromSource(cls, source, name, parent):
        id_ = source.tags_table.AddTag(name, parent)
        return cls(source, id_, name, parent)

    @classmethod
    def ListFromParent(cls, source, parent):
        return [
            cls(source, t["id"], t["name"], parent)
            for t in source.tags_table.GetTable(parent)
        ]

    @staticmethod
    def _DeleteIdAndChildren(source, id_):
        source.tags_table.Delete((id_,))
        for t in source.tags_table.GetTable(id_):
            Tag._DeleteIdAndChildren(source, t["id"])

    @staticmethod
    def TagNames(source):
        tags = source.tags_table.GetTable()
        return [t["name"] for t in tags]


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

    ROOT_FLAGS = Qt.ItemIsEnabled
    WEB_SOURCE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable
    LOCAL_SOURCE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
    TAG_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def __init__(self, parent=None):
        super(SourceModel, self).__init__(parent)

        root = self.invisibleRootItem()
        self.TagBeingCreated = None

        web_search = QStandardItem(QIcon(icons.WEB), "Web Search")
        web_search.setFlags(SourceModel.ROOT_FLAGS)
        local = QStandardItem(QIcon(icons.LOCAL), "Local")
        local.setFlags(SourceModel.ROOT_FLAGS)

        root.setChild(0, web_search)
        root.setChild(1, local)

        self.ITEMS = {}
        for (r, (n, s)) in enumerate(SourceModel.WEB_SOURCES.items()):
            i = SourceModel._CreateItemFromData(s)
            self.ITEMS[n] = i
            web_search.setChild(r, i)

        for (r, (n, p)) in enumerate(LOCAL_DATABASES.items()):
            if not os.path.isfile(p):
                print("Error: Cannot find database file", p)
                continue

            s = LocalSource(n, p)
            i = SourceModel._CreateItemFromData(s)
            local.setChild(r, i)
            SourceModel._AppendTags(s, i)
            # i.sortChildren(0, Qt.AscendingOrder)

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

    def AddTag(self, item, view):
        data = item.data()
        if isinstance(data, LocalSource):
            source = data
            parent = 0
        else:
            source = data.source
            parent = data.id

        tag = Tag(source, None, "", parent)
        tag_item = SourceModel._CreateItemFromData(tag)

        item.insertRow(0, tag_item)
        item.setChild(0, tag_item)

        view.setExpanded(self.indexFromItem(item), True)
        self.TagBeingCreated = tag_item
        # view.setCurrentIndex(self.indexFromItem(tag_item))
        view.edit(self.indexFromItem(tag_item))

    def HandleNoUpdate(self):
        if self.TagBeingCreated is None:
            return
        self.RemoveTag(self.TagBeingCreated)
        self.TagBeingCreated = None

    def RemoveTag(self, item):
        tag = item.data()
        if tag.id is not None:
            tag.Delete()

        parent = self.indexFromItem(item.parent())
        self.removeRow(item.row(), parent)

    @staticmethod
    def _CreateItemFromData(data):
        if type(data) == WebSource:
            item = QStandardItem(QIcon(data.icon), data.name)
            item.setFlags(SourceModel.WEB_SOURCE_FLAGS)
        elif type(data) == LocalSource:
            item = QStandardItem(QIcon(icons.DATABASE), data.name)
            item.setFlags(SourceModel.LOCAL_SOURCE_FLAGS)
        elif type(data) == Tag:
            item = QStandardItem(QIcon(icons.TAG), data.name)
            item.setFlags(SourceModel.TAG_FLAGS)

        item.setData(data)
        return item

    @staticmethod
    def _AppendTags(source, item):
        data = item.data()
        if isinstance(data, LocalSource):
            parent = 0
        else:
            parent = data.id

        for (r, t) in enumerate(Tag.ListFromParent(source, parent)):
            i = SourceModel._CreateItemFromData(t)
            item.setChild(r, i)
            SourceModel._AppendTags(source, i)


class SourcePanel(QTreeView):
    SearchRequested = Signal(dict)
    WebSourceSelected = Signal()
    LocalSourceSelected = Signal(LocalSource)
    # SourceSelected = Signal((WebSource,), (LocalSource,))

    def __init__(self, parent=None):
        super(SourcePanel, self).__init__(parent)

        self._delegate = SourceDelegate()
        self.setItemDelegate(self._delegate)

        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        self.setWordWrap(True)
        self.setHeaderHidden(True)

        self.setDragDropMode(QAbstractItemView.DropOnly)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._HandleRightClickOnItem)

    def setModel(self, model):
        if self.model() is not None:
            self._delegate.EditorNoUpdate.disconnect(self.model().HandleNoUpdate)

        super(SourcePanel, self).setModel(model)

        self._delegate.EditorNoUpdate.connect(self.model().HandleNoUpdate)

        self.expandAll()

    # def mousePressEvent(self, event):
    #     # We reimplement this to prevent right clicks from selecting sources
    #     if event.button() == Qt.RightButton:
    #         index = self.indexAt(event.pos())
    #         if index.isValid():
    #             self.selectionModel().setCurrentIndex(index, QItemSelectionModel.Current)
    #     else:
    #         super(SourcePanel, self).mousePressEvent(event)

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

        data = self.model().itemFromIndex(rows[0]).data()
        if isinstance(data, Tag):
            source = data.source
            # Emit appropriate signal
        else:
            source = data

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

        data = self.model().itemFromIndex(rows[0]).data()

        if isinstance(data, WebSource):
            self.SearchRequested.emit(data.CreateSearch(query))

    def _HandleRightClickOnItem(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        item = self.model().itemFromIndex(index)
        data = item.data()

        if isinstance(data, LocalSource):
            menu = self._ContextMenuLocalSource(item)
            menu.exec_(self.viewport().mapToGlobal(position))

        if isinstance(data, Tag):
            menu = self._ContextMenuTag(item)
            menu.exec_(self.viewport().mapToGlobal(position))

    def _ContextMenuLocalSource(self, item):
        menu = QMenu()

        action_open = menu.addAction(QIcon(icons.OPEN), "Open folder")
        action_new_tag = menu.addAction(QIcon(icons.TAG_NEW), "New tag")

        path = os.path.dirname(item.data().database.file)
        action_open.triggered.connect(partial(self._OpenPath, path))

        action_new_tag.triggered.connect(partial(self.model().AddTag, item, self))

        return menu

    def _ContextMenuTag(self, item):
        menu = QMenu()

        action_new_tag = menu.addAction(QIcon(icons.TAG_NEW), "New tag")
        action_remove_tag = menu.addAction(QIcon(icons.DELETE), "Remove Tag")

        action_new_tag.triggered.connect(partial(self.model().AddTag, item, self))
        action_remove_tag.triggered.connect(partial(self.model().RemoveTag, item))

        return menu

    @staticmethod
    def _OpenPath(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


class SourceDelegate(QStyledItemDelegate):
    EditorNoUpdate = Signal()

    def __init__(self, parent=None):
        super(SourceDelegate, self).__init__(parent)
        self.closeEditor.connect(self.HandleCloseEditor)

    def setModelData(self, editor, model, index):
        editor.setText(editor.text().strip())
        item = model.itemFromIndex(index)

        tag_names = Tag.TagNames(item.data().source)
        if editor.text() in tag_names + [""]:
            self.EditorNoUpdate.emit()
            # Possibly, display an error message.
            return

        super(SourceDelegate, self).setModelData(editor, model, index)
        SourceDelegate.RenameTag(model, item)
        item.parent().sortChildren(0, Qt.AscendingOrder)

    def HandleCloseEditor(self, editor, hint):
        discard = hint in (
            QAbstractItemDelegate.EndEditHint.NoHint,
            QAbstractItemDelegate.EndEditHint.RevertModelCache
        )
        if discard:
            self.EditorNoUpdate.emit()

    @staticmethod
    def RenameTag(model, item):
        tag = item.data()
        name = item.text()
        if model.TagBeingCreated is None:
            tag.Rename(name)
        else:
            item.setData(Tag.CreateFromSource(tag.source, name, tag.parent))
            model.TagBeingCreated = None
