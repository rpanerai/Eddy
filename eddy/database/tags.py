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
        query = f"INSERT INTO {self._name} (name, parent) VALUES (?,?)"

        cursor = self.Cursor()
        cursor.execute(query, (name, parent))

        return cursor.lastrowid

    def ChildTags(self, parent, recursive=False):
        keys = ["id", "name"]
        if recursive:
            query = (
                f"WITH RECURSIVE cte_{self._name} (id, name, parent) AS ( "
                f"SELECT t.id, t.name, t.parent FROM {self._name} t WHERE t.parent = ? "
                f"UNION ALL "
                f"SELECT t.id, t.name, t.parent FROM {self._name} t "
                f"JOIN cte_{self._name} c ON c.id = t.parent "
                f") "
                f"SELECT {', '.join(keys)} FROM cte_{self._name}"
            )
        else:
            query = f"SELECT {', '.join(keys)} FROM {self._name} WHERE parent = ?"

        cursor = self.Cursor()
        cursor.execute(query, (parent,))
        children = [dict(zip(keys, t)) for t in cursor.fetchall()]
        # for k in self._DECODE_FUNCTIONS:
        #     if k in keys:
        #         for d in data:
        #             d[k] = self._DECODE_FUNCTIONS[k](d[k])

        return children
