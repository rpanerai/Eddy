import sqlite3
import json

from PySide2.QtCore import QObject, Signal


class Database(QObject):
    def __init__(self, parent=None):
        super(Database, self).__init__(parent)
        self.connection = sqlite3.connect(":memory:")


DATABASE_IN_MEMORY = Database()


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

    _ENCODE_FUNCTIONS = {
        "authors": json.dumps,
        "dois": json.dumps
    }

    _DECODE_FUNCTIONS = {
        "authors": json.loads,
        "dois": json.loads
    }

    def __init__(self, database, name, parent=None):
        super(Table, self).__init__(parent)

        self._connection = database.connection
        self._name = name

    def __del__(self):
        cursor = self._connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS " + self._name)

    def Clear(self):
        cursor = self._connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS " + self._name)

        keys = ", ".join([k + " " + t for k, t in Table._KEYS.items()])
        cursor.execute("CREATE TABLE " + self._name + " (" + keys + ")")

        self.Cleared.emit()

    def AddData(self, data):
        placeholder = "(" + ', '.join('?' * len(Table._KEYS))+ ")"
        query = "INSERT INTO " + self._name + " VALUES " + placeholder
        values = [
            tuple([
                Table._ENCODE_FUNCTIONS.get(k, lambda x: x)(d[k])
                for k in Table._KEYS
            ])
            for d in data
        ]
        cursor = self._connection.cursor()
        cursor.executemany(query, values)

        self.Updated.emit()

    def GetTable(self, keys, filter_string=None, sort_key=None, sort_order="DESC"):
        query = "SELECT " + ", ".join(keys) + " FROM " + self._name
        if filter_string is not None:
            query = query + " WHERE title LIKE '" + filter_string + "'"
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
