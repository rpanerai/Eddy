from eddy.database.database import Table


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
        super().__init__(database, name, drop_on_del, parent)

    def AddTag(self, name, parent=0):
        query = "INSERT INTO " + self._name + " (name, parent) VALUES (?,?)"

        cursor = self._connection.cursor()
        cursor.execute(query, (name, parent))

        return cursor.lastrowid

    def GetTable(self, parent=None):
        if parent is None:
            return super().GetTable(keys=None)

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

    def ChildTags(self, parent):
        query = (
            "WITH RECURSIVE cte_" + self._name + " (id, parent) AS ( "
            "SELECT t.id, t.parent FROM " + self._name + " t WHERE t.parent = ? "
            "UNION ALL "
            "SELECT t.id, t.parent FROM " + self._name + " t "
            "JOIN cte_" + self._name + " c ON c.id = t.parent "
            ") "
            "SELECT id FROM cte_" + self._name
        )
        cursor = self._connection.cursor()
        cursor.execute(query, (parent,))
        children = [t for (t,) in cursor.fetchall()]
        return children
