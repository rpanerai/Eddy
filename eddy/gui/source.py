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

from paths import STORAGE_FOLDER, LOCAL_DATABASES
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

    def FilesDir(self):
        dir_ = os.path.join(os.path.dirname(os.path.realpath(self.database.file)), STORAGE_FOLDER)
        if not os.path.isdir(dir_):
            try:
                os.mkdir(dir_)
            except:
                return None
        return dir_

    def SaveFiles(self, paths):
        files_dir = self.FilesDir()

        copies = []
        renamings = {}
        for path in paths:
            file_ = os.path.basename(path)
            new_path = os.path.join(files_dir, file_)
            i = 1
            while os.path.exists(new_path):
                i = i + 1
                (body, ext) = os.path.splitext(new_path)
                new_path = body + "(" + str(i) + ")" + ext
            copies.append((path, new_path))
            if i > 1:
                renamings[file_] = os.path.basename(new_path)

        for c in copies:
            shutil.copy2(*c)

        return renamings

    def AssignToTag(self, ids, tag_id):
        for i in ids:
            r = self.table.GetRow(i, ("tags",))
            if tag_id not in r["tags"]:
                r["tags"].append(tag_id)
                self.table.EditRow(i, r)

    def DropTagFromItem(self, id_, tag_id):
        record = self.table.GetRow(id_, ("tags",))
        record["tags"].remove(tag_id)
        self.table.EditRow(id_, record)

    def DropTag(self, tag_id):
        items = self.table.GetTable(("id", "tags"), tags=(tag_id,))
        for i in items:
            i["tags"].remove(tag_id)
            self.table.EditRow(i["id"], {"tags": i["tags"]})

    def TagNames(self):
        tags = self.tags_table.GetTable()
        return [t["name"] for t in tags]

    def TagMap(self):
        tags = self.tags_table.GetTable()
        return {t["id"]: t["name"] for t in tags}


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
        self._DeleteIdAndChildren(self.id)

    def _DeleteIdAndChildren(self, id_):
        self.source.tags_table.Delete((id_,))
        self.source.DropTag(id_)
        for t in self.source.tags_table.GetTable(id_):
            self._DeleteIdAndChildren(t["id"])

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
    TAG_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDropEnabled

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
        if isinstance(target, LocalSource):
            # Prevent drops when origin and target databases coincide
            origin_file = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))[0]
            return target.database.file != origin_file

        if isinstance(target, Tag):
            return True

        return False

    def dropMimeData(self, data, action, row, column, parent):
        (origin_file, ids, records) = json.loads(str(data.data(self.mimeTypes()[0]), 'utf-8'))
        target = self.itemFromIndex(parent).data()

        if isinstance(target, LocalSource):
            return SourceModel._DropIntoSource(target, origin_file, records)

        if isinstance(target, Tag):
            if target.source.database.file == origin_file:
                target.source.AssignToTag(ids, target.id)
                return True
            return SourceModel._DropIntoSource(target.source, origin_file, records, target.id)

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
    def ChildTagIds(item):
        ids = []
        i = 0
        while (c := item.child(i)) is not None:
            ids.append(c.data().id)
            ids = ids + SourceModel.ChildTagIds(c)
            i = i + 1
        return ids

    @staticmethod
    def _CreateItemFromData(data):
        if isinstance(data, WebSource):
            item = QStandardItem(QIcon(data.icon), data.name)
            item.setFlags(SourceModel.WEB_SOURCE_FLAGS)
        elif isinstance(data, LocalSource):
            item = QStandardItem(QIcon(icons.DATABASE), data.name)
            item.setFlags(SourceModel.LOCAL_SOURCE_FLAGS)
        elif isinstance(data, Tag):
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

    @staticmethod
    def _DropIntoSource(target, origin_file, records, tag=None):
        # In copying items, we drop their citations and tags fields.
        for d in records:
            d.pop("citations")
            d.pop("tags")

        if tag is not None:
            for d in records:
                d["tags"] = [tag]

        # If no files are involved in the drop action, simply add the items to the target database.
        if origin_file == ":memory:":
            target.table.AddData(records)
            return True

        files = []
        for d in records:
            files = files + d["files"]
        files = set(files)
        if len(files) == 0:
            target.table.AddData(records)
            return True

        # If the Files folder is shared between origin and target, there is no need to copy files.
        origin_dir = os.path.join(os.path.dirname(os.path.realpath(origin_file)), STORAGE_FOLDER)
        target_dir = target.FilesDir()
        if target_dir == origin_dir:
            target.table.AddData(records)
            return True

        # Check that the Files folder is accessible.
        if target_dir is None:
            QMessageBox.critical(
                None, "Error", "Cannot access storage folder. Drop action aborted."
            )
            return False

        # Copy files in the target folder and add the items to the target database.
        paths = [os.path.join(origin_dir, f) for f in files]
        try:
            renamings = target.SaveFiles(paths)
        except:
            QMessageBox.critical(None, "Error", "Error while copying files. Drop action aborted.")
            return False
        else:
            for r in records:
                r["files"] = [renamings.get(f, f) for f in r["files"]]
            target.table.AddData(records)
            return True


class SourcePanel(QTreeView):
    SearchRequested = Signal(dict)
    WebSourceSelected = Signal()
    LocalSourceSelected = Signal(LocalSource, list)
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

        item = self.model().itemFromIndex(rows[0])
        data = item.data()
        tag_ids = []
        if isinstance(data, Tag):
            source = data.source
            tag_ids = [data.id] + self.model().ChildTagIds(item)
        else:
            source = data

        if isinstance(source, LocalSource):
            self.LocalSourceSelected.emit(source, tag_ids)
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

        tag_names = item.data().source.TagNames()
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
