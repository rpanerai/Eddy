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

    def ChildTagsIds(self):
        return self.source.tags_table.ChildTags(self.id)

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
