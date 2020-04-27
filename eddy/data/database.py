import sqlite3
import json

from PySide2.QtCore import QObject, Signal


class Database(QObject):
    def __init__(self, file=":memory:", parent=None):
        super(Database, self).__init__(parent)

        self._file = file
        self.connection = sqlite3.connect(self._file, isolation_level=None)

    def __del__(self):
        self.connection.close()
        print("Closing connection to database '" + self._file + "'")


class Table(QObject):
    Cleared = Signal()
    Updated = Signal()

    _KEYS = {
        "id": "INTEGER PRIMARY KEY",
        "type": "TEXT",
        "date": "TEXT",
        "authors": "TEXT",
        "title": "TEXT",
        "abstract": "TEXT",
        "journal": "TEXT",
        "citations": "INTEGER",
        "inspire_id": "INTEGER",
        "texkey": "TEXT",
        "arxiv_id": "TEXT",
        "dois": "TEXT"
    }

    _DEFAULTS = {
        "type": None,
        "date": None,
        "authors": [],
        "title": None,
        "abstract": None,
        "journal": None,
        "citations": None,
        "inspire_id": None,
        "texkey": None,
        "arxiv_id": None,
        "dois": []
    }

    _ENCODE_FUNCTIONS = {
        "authors": json.dumps,
        "dois": json.dumps
    }

    _DECODE_FUNCTIONS = {
        "authors": json.loads,
        "dois": json.loads
    }

    def __init__(self, database, name, drop_on_del=False, parent=None):
        super(Table, self).__init__(parent)

        self._database = database
        self._connection = database.connection
        self._name = name
        self._drop_on_del = drop_on_del

    def __del__(self):
        if self._drop_on_del:
            cursor = self._connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS " + self._name)
            print("Dropping table '" + self._name + "'")

    def Clear(self):
        cursor = self._connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS " + self._name)

        keys = ", ".join([k + " " + t for k, t in Table._KEYS.items()])
        cursor.execute("CREATE TABLE " + self._name + " (" + keys + ")")

        self.Cleared.emit()

    def AddData(self, data):
        keys = self._DEFAULTS.keys()

        keys_str = "(" + ', '.join(keys) + ")"
        placeholder = "(" + ', '.join('?' * len(keys)) + ")"
        query = "INSERT INTO " + self._name + keys_str + " VALUES " + placeholder
        values = [
            tuple([
                Table._ENCODE_FUNCTIONS.get(k, lambda x: x)(d.get(k, self._DEFAULTS[k]))
                for k in keys
            ])
            for d in data
        ]
        cursor = self._connection.cursor()
        cursor.executemany(query, values)

        self.Updated.emit()

    def Delete(self, ids):
        query = "DELETE FROM " + self._name + " WHERE id = ?"
        ids = [(i,) for i in ids]
        
        cursor = self._connection.cursor()
        cursor.executemany(query, ids)

        self.Updated.emit()

    def GetTable(self, keys, sort_key=None, sort_order="DESC", filter_strings=()):
        query = "SELECT " + ", ".join(keys) + " FROM " + self._name
        for i, s in enumerate(filter_strings):
            query = query + (" WHERE " if i == 0 else " AND ")
            query = query + "authors || title LIKE '%" + s + "%'"
        if sort_key is not None:
            query = query + " ORDER BY " + sort_key + " " + sort_order

        cursor = self._connection.cursor()
        cursor.execute(query)
        data = [dict(zip(keys, t)) for t in cursor.fetchall()]
        for k in Table._DECODE_FUNCTIONS:
            if k in keys:
                for d in data:
                    d[k] = Table._DECODE_FUNCTIONS[k](d[k])

        return data

    def GetRecord(self, id_, keys):
        query = "SELECT " + ", ".join(keys) + " FROM " + self._name + " WHERE id = " + str(id_)

        cursor = self._connection.cursor()
        cursor.execute(query)
        data = dict(zip(keys, cursor.fetchone()))
        for k in Table._DECODE_FUNCTIONS:
            if k in keys:
                data[k] = Table._DECODE_FUNCTIONS[k](data[k])

        return data
