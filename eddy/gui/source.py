from functools import partial
import itertools
import json
from pathlib import Path

from PySide2.QtCore import Qt, Signal, QItemSelectionModel
from PySide2.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide2.QtWidgets import (
    QTreeView, QAbstractItemView, QAbstractItemDelegate, QStyledItemDelegate, QMenu, QMessageBox
)

from config import LOCAL_DATABASES
from eddy.icons import icons
from eddy.core.web import WebSource, WEB_SOURCES, CHILD_SOURCES
from eddy.core.local import STORAGE_FOLDER, LocalSource
from eddy.core.tag import Tag, TagBuilder
from eddy.core.platform import OpenFolder


class SourceModel(QStandardItemModel):
    ROOT_FLAGS = Qt.ItemIsEnabled
    WEB_SOURCE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable
    LOCAL_SOURCE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
    TAG_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDropEnabled
    TAG_BUILDER_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsEditable

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ITEMS = {}

        root = self.invisibleRootItem()
        self.TagBeingCreated = None

        web_search = QStandardItem(QIcon(icons.WEB), "Web")
        web_search.setFlags(SourceModel.ROOT_FLAGS)
        local = QStandardItem(QIcon(icons.LOCAL), "Local")
        local.setFlags(SourceModel.ROOT_FLAGS)

        def embolden_item(item):
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        embolden_item(web_search)
        embolden_item(local)

        root.setChild(0, web_search)
        root.setChild(1, local)

        for (r, s) in enumerate(WEB_SOURCES):
            i = SourceModel._CreateItemFromData(s)
            self[s.name] = i
            web_search.setChild(r, i)
        for (p, l) in CHILD_SOURCES.items():
            for (r, s) in enumerate(l):
                i = SourceModel._CreateItemFromData(s)
                self[s.name] = i
                self[p].setChild(r, i)

        for (r, (n, p)) in enumerate(LOCAL_DATABASES.items()):
            if not Path(p).is_file():
                print(f"Error: Cannot find database file {p}")
                continue

            s = LocalSource(n, p)
            i = SourceModel._CreateItemFromData(s)
            local.setChild(r, i)
            SourceModel._AppendTags(i)
            i.sortChildren(0, Qt.AscendingOrder)
    
    def __getitem__(self, name):
        return self._ITEMS[name]
    
    def __setitem__(self, name, item):
        self._ITEMS[name] = item

    def mimeTypes(self):
        return ["application/x-eddy"]

    def canDropMimeData(self, data, action, row, column, parent):
        # Drop only on valid indices, where parent is the index and row = column = -1.
        if (row, column) != (-1, -1):
            return False
        if not parent.isValid():
            return False

        match target := self.itemFromIndex(parent).data():
            case LocalSource():
                # Prevent drops when origin and target databases coincide
                origin_file = json.loads(str(data.data(*self.mimeTypes()), 'utf-8'))[0]
                return str(target.database.file) != origin_file
            case Tag():
                return True
            case _:
                return False

    def dropMimeData(self, data, action, row, column, parent):
        (origin_file, ids, records) = json.loads(str(data.data(*self.mimeTypes()), 'utf-8'))
        match target := self.itemFromIndex(parent).data():
            case LocalSource():
                return SourceModel._DropIntoSource(target, origin_file, records)
            case Tag():
                if str(target.source.database.file) == origin_file:
                    target.source.AssignToTag(ids, target.id)
                    return True
                return SourceModel._DropIntoSource(target.source, origin_file, records, target.id)
            case _:
                return False

    def AddTag(self, parent_item):
        data = parent_item.data()
        if isinstance(data, LocalSource):
            data = data.RootTag()

        tag_builder = data.ChildTagBuilder()
        tag_item = SourceModel._CreateItemFromData(tag_builder)
        parent_item.insertRow(0, tag_item)
        parent_item.setChild(0, tag_item)

        self.TagBeingCreated = tag_item
        return tag_item

    def HandleNoUpdate(self):
        if self.TagBeingCreated is None:
            return

        item = self.TagBeingCreated
        parent = self.indexFromItem(item.parent())
        self.removeRow(item.row(), parent)

        self.TagBeingCreated = None

    def RemoveTag(self, item):
        item.data().Delete()

        parent = self.indexFromItem(item.parent())
        self.removeRow(item.row(), parent)

    @staticmethod
    def _CreateItemFromData(data):
        match data:
            case WebSource():
                item = QStandardItem(QIcon(data.icon), data.name)
                item.setFlags(SourceModel.WEB_SOURCE_FLAGS)
            case LocalSource():
                item = QStandardItem(QIcon(icons.DATABASE), data.name)
                item.setFlags(SourceModel.LOCAL_SOURCE_FLAGS)
            case Tag():
                item = QStandardItem(QIcon(icons.TAG), data.name)
                item.setFlags(SourceModel.TAG_FLAGS)
            case TagBuilder():
                item = QStandardItem(QIcon(icons.TAG), "")
                item.setFlags(SourceModel.TAG_BUILDER_FLAGS)

        item.setData(data)
        return item

    @staticmethod
    def _AppendTags(item):
        data = item.data()
        if isinstance(data, LocalSource):
            data = data.RootTag()

        for (j, t) in enumerate(data.ListChildren()):
            i = SourceModel._CreateItemFromData(t)
            item.setChild(j, i)
            SourceModel._AppendTags(i)

    @staticmethod
    def _DropIntoSource(target, origin_file, records, tag=None):
        for d in records:
            d.pop("citations")
            d.pop("tags")

        if tag is not None:
            for d in records:
                d["tags"] = [tag]

        if origin_file == ":memory:":
            target.table.AddData(records)
            return True

        files = set(itertools.chain(*[d["files"] for d in records]))
        if len(files) == 0:
            target.table.AddData(records)
            return True

        origin_dir = Path(origin_file).parent / STORAGE_FOLDER
        paths = [origin_dir / f for f in files]
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
    WebSourceSelected = Signal(WebSource)
    LocalSourceSelected = Signal(LocalSource, list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setItemDelegate(SourceDelegate())
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(False)
        self.setWordWrap(True)
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._HandleRightClickOnItem)

    @property
    def _model(self):
        return self.model()
    
    @property
    def _delegate(self):
        return self.itemDelegate()

    def setModel(self, model):
        if self._model is not None:
            self._delegate.EditorNoUpdate.disconnect(self._model.HandleNoUpdate)

        super().setModel(model)

        self._delegate.EditorNoUpdate.connect(self._model.HandleNoUpdate)
        self.expandAll()

    # def mousePressEvent(self, event):
    #     # We reimplement this to prevent right clicks from selecting sources
    #     if event.button() == Qt.RightButton:
    #         index = self.indexAt(event.pos())
    #         if index.isValid():
    #             self.selectionModel().setCurrentIndex(index, QItemSelectionModel.Current)
    #     else:
    #         super().mousePressEvent(event)

    def selectionCommand(self, index, event):
        # selection_flags = super().selectionCommand(index, event)

        # NOTE: selectionCommand returns QItemSelectionModel.SelectionFlag
        # Then enum value corresponding to the flag can be accessed with int().
        # In the current setup, two values are produced:
        # Clear | Select | Rows -> 35
        # Deselect | Rows -> 36

        if not index.isValid():
            return QItemSelectionModel.NoUpdate

        if not self._model.itemFromIndex(index).isSelectable():
            return QItemSelectionModel.NoUpdate

        return QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)

        rows = self.selectionModel().selectedRows()
        if len(rows) != 1:
            return

        match data := self._model.itemFromIndex(*rows).data():
            case WebSource():
                self.WebSourceSelected.emit(data)
            case LocalSource():
                self.LocalSourceSelected.emit(data, [])
            case Tag():
                tags = [data] + data.ListChildren(recursive=True)
                self.LocalSourceSelected.emit(data.source, tags)

    def SelectSource(self, source):
        index = self._model.indexFromItem(self._model[source.name])
        selection_model = self.selectionModel()
        if selection_model.selectedRows() != [index]:
            selection_model.select(
                index,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )

    def _HandleRightClickOnItem(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        item = self._model.itemFromIndex(index)
        match item.data():
            case LocalSource():
                menu = self._ContextMenuLocalSource(item)
                menu.exec_(self.viewport().mapToGlobal(position))
            case Tag():
                menu = self._ContextMenuTag(item)
                menu.exec_(self.viewport().mapToGlobal(position))

    def _ContextMenuLocalSource(self, item):
        menu = QMenu()

        action_new_tag = menu.addAction(QIcon(icons.TAG_NEW), "New tag")
        menu.addSeparator()
        action_open = menu.addAction(QIcon(icons.OPEN), "Open folder")
        action_check_files = menu.addAction(
            QIcon(icons.FILE_CHECK), "Find missing and orphan files…")

        source = item.data()
        action_new_tag.triggered.connect(partial(self._AddTag, item))
        action_open.triggered.connect(partial(OpenFolder, source.database.file.parent))
        action_check_files.triggered.connect(source.CheckFiles)

        return menu

    def _ContextMenuTag(self, item):
        menu = QMenu()

        action_new_tag = menu.addAction(QIcon(icons.TAG_NEW), "New tag")
        action_remove_tag = menu.addAction(QIcon(icons.DELETE), "Remove Tag")

        action_new_tag.triggered.connect(partial(self._AddTag, item))
        action_remove_tag.triggered.connect(partial(self._model.RemoveTag, item))

        return menu

    def _AddTag(self, parent_item):
        self.setExpanded(self._model.indexFromItem(parent_item), True)
        tag_item = self._model.AddTag(parent_item)
        self.edit(self._model.indexFromItem(tag_item))


class SourceDelegate(QStyledItemDelegate):
    EditorNoUpdate = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.closeEditor.connect(self.HandleCloseEditor)

    def setModelData(self, editor, model, index):
        editor.setText(editor.text().strip())
        item = model.itemFromIndex(index)

        tag_names = item.data().source.TagNames()
        if editor.text() in tag_names + [""]:
            self.EditorNoUpdate.emit()
            # Possibly, display an error message.
            return

        super().setModelData(editor, model, index)
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
            item.setData(tag.Build(name))
            item.setFlags(SourceModel.TAG_FLAGS)
            model.TagBeingCreated = None
