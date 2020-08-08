import os
import shutil

from paths import STORAGE_FOLDER
from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.database.tags import TagsTable


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
