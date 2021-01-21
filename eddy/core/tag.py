from abc import ABC, abstractmethod


class TagBuilder:
    def __init__(self, source, parent):
        self.source = source
        self.parent = parent

    def Build(self, name):
        id_ = self.source.tags_table.AddTag(name, self.parent)
        return Tag(self.source, id_, name, self.parent)


class AbstractTag(ABC):
    @abstractmethod
    def __init__(self, source, id_):
        self.source = source
        self.id = id_

    def ListChildren(self, recursive=False):
        return [
            Tag(self.source, t["id"], t["name"], self.id)
            for t in self.source.tags_table.ChildTags(self.id, recursive=recursive)
        ]

    def ChildTagBuilder(self):
        return TagBuilder(self.source, self.id)


class RootTag(AbstractTag):
    def __init__(self, source):
        super().__init__(source, 0)


class Tag(AbstractTag):
    def __init__(self, source, id_, name, parent):
        super().__init__(source, id_)
        self.name = name
        self.parent = parent

    def Rename(self, name):
        self.source.tags_table.EditRow(self.id, {"name": name})
        self.name = name

    def Delete(self):
        self.source.DeleteTagAndChildren(self.id)
