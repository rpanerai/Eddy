import json

from eddy.data.database import Table


class TagsTable(Table):
    _KEYS = {
        "id": "INTEGER PRIMARY KEY",
        "name": "TEXT",
        "parent": "INTEGER"
    }

    _DEFAULTS = {
        "name": "",
        "parent": 0
    }

    _ENCODE_FUNCTIONS = {}

    _DECODE_FUNCTIONS = {}

    def __init__(self, database, name="tags", drop_on_del=False, parent=None):
        super(TagsTable, self).__init__(database, name, drop_on_del, parent)

    def AddTag(self, name, parent=0):
        query = "INSERT INTO " + self._name + " (name, parent) VALUES (?,?)"

        cursor = self._connection.cursor()
        cursor.execute(query, (name, parent))

        return cursor.lastrowid

    def GetTable(self, parent=None):
        if parent is None:
            return super(TagsTable, self).GetTable(keys=None)

        keys = ["id", "name"]
        query = ("SELECT " + ", ".join(keys) + " FROM " + self._name
                 + " WHERE parent = " + str(parent))

        cursor = self._connection.cursor()
        cursor.execute(query)
        data = [dict(zip(keys, t)) for t in cursor.fetchall()]
        for k in self._DECODE_FUNCTIONS:
            if k in keys:
                for d in data:
                    d[k] = self._DECODE_FUNCTIONS[k](d[k])

        return data
