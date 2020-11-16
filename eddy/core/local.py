import os
import shutil
import itertools

from eddy.core.tag import Tag, RootTag
from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.database.tags import TagsTable


STORAGE_FOLDER = "Files"


class LocalSource:
    def __init__(self, name, file):
        self.name = name
        self.database = Database(os.path.realpath(file))
        self.table = ItemsTable(self.database)
        self.tags_table = TagsTable(self.database)

    def FilesDir(self):
        dir_ = os.path.join(os.path.dirname(self.database.file), STORAGE_FOLDER)
        if not os.path.isdir(dir_):
            os.mkdir(dir_)
        return dir_

    def SaveFiles(self, paths):
        paths = set(map(os.path.realpath, paths))
        files_dir = self.FilesDir()

        renamings = {}
        for path in paths:
            file_ = os.path.basename(path)
            new_path = os.path.join(files_dir, file_)
            if path == new_path:
                continue
            i = 1
            while os.path.exists(new_path):
                i = i + 1
                (body, ext) = os.path.splitext(new_path)
                new_path = body + "(" + str(i) + ")" + ext
            shutil.copy2(path, new_path)
            if i > 1:
                renamings[file_] = os.path.basename(new_path)

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

    def RootTag(self):
        return RootTag(self)

    def AddTag(self, name, parent):
        id_ = self.tags_table.AddTag(name, parent)
        return Tag(self, id_, name, parent)

    def DropTag(self, tag_id):
        items = self.table.GetTable(("id", "tags"), tags=(tag_id,))
        for i in items:
            i["tags"].remove(tag_id)
            self.table.EditRow(i["id"], {"tags": i["tags"]})

    def DeleteTagAndChildren(self, id_):
        self.tags_table.Delete((id_,))
        self.DropTag(id_)
        for t in self.tags_table.GetTable(id_):
            self.DeleteTagAndChildren(t["id"])

    def TagNames(self):
        tags = self.tags_table.GetTable()
        return [t["name"] for t in tags]

    def TagMap(self):
        tags = self.tags_table.GetTable()
        return {t["id"]: t["name"] for t in tags}

    def CheckFiles(self):
        (_, _, files_present) = next(os.walk(self.FilesDir()))
        files_present = set(files_present)

        records = self.table.GetTable(("files",))
        files_needed = set(itertools.chain(*[d["files"] for d in records]))

        orphans = files_present - files_needed
        missing = files_needed - files_present

        dir_ = os.path.dirname(self.database.file)
        with open(os.path.join(dir_, self.name + "_orphans.txt"), "w") as f:
            for s in orphans:
                f.write(f"{s}\n")
        with open(os.path.join(dir_, self.name + "_missing.txt"), "w") as f:
            for s in missing:
                f.write(f"{s}\n")
