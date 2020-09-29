import sqlite3

from PySide2.QtCore import QObject, Signal


class Database(QObject):
    def __init__(self, file=":memory:", parent=None):
        super().__init__(parent)

        self.file = file
        self.connection = sqlite3.connect(self.file, isolation_level=None)

    def __del__(self):
        self.connection.close()
        print("Closing connection to database '" + self.file + "'")


class Table(QObject):
    Cleared = Signal()
    Updated = Signal()

    _KEYS = {"id": "INTEGER PRIMARY KEY"}

    _DEFAULTS = {}

    _ENCODE_FUNCTIONS = {}

    _DECODE_FUNCTIONS = {}

    def __init__(self, database, name, drop_on_del=False, parent=None):
        super().__init__(parent)

        self.database = database
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

        keys = ", ".join([k + " " + t for k, t in self._KEYS.items()])
        cursor.execute("CREATE TABLE " + self._name + " (" + keys + ")")

        self.Cleared.emit()

    def AddData(self, data):
        keys = self._DEFAULTS.keys()

        keys_str = "(" + ', '.join(keys) + ")"
        placeholder = "(" + ', '.join('?' * len(keys)) + ")"
        query = "INSERT INTO " + self._name + keys_str + " VALUES " + placeholder
        values = [
            tuple(
                self._ENCODE_FUNCTIONS.get(k, lambda x: x)(d.get(k, self._DEFAULTS[k]))
                for k in keys
            )
            for d in data
        ]
        cursor = self._connection.cursor()

        # To get a valid lastrowid, we need to call execute() rather than executemany().
        if len(values) == 1:
            cursor.execute(query, values[0])
        else:
            cursor.executemany(query, values)

        self.Updated.emit()
        return cursor.lastrowid

    def Delete(self, ids):
        query = "DELETE FROM " + self._name + " WHERE id = ?"
        ids = [(i,) for i in ids]

        cursor = self._connection.cursor()
        cursor.executemany(query, ids)

        self.Updated.emit()

    def GetRow(self, id_, keys=None):
        if keys is None:
            keys_ = self._DEFAULTS.keys()
        else:
            keys_ = list({k for k in keys if k in self._DEFAULTS.keys()})

        query = "SELECT " + ", ".join(keys_) + " FROM " + self._name + " WHERE id = " + str(id_)

        cursor = self._connection.cursor()
        cursor.execute(query)
        data = dict(zip(keys_, cursor.fetchone()))
        for k in self._DECODE_FUNCTIONS:
            if k in keys_:
                data[k] = self._DECODE_FUNCTIONS[k](data[k])

        return data

    def GetTable(self, keys=None):
        if keys is None:
            keys_ = self._KEYS.keys()
        else:
            keys_ = list({k for k in keys if k in self._KEYS.keys()})

        query = "SELECT " + ", ".join(keys_) + " FROM " + self._name

        cursor = self._connection.cursor()
        cursor.execute(query)
        data = [dict(zip(keys_, t)) for t in cursor.fetchall()]
        for k in self._DECODE_FUNCTIONS:
            if k in keys_:
                for d in data:
                    d[k] = self._DECODE_FUNCTIONS[k](d[k])

        return data

    def EditRow(self, id_, data):
        keys = [k for k in data.keys() if k in self._DEFAULTS.keys()]

        keys_str = "(" + ', '.join(keys) + ")"
        placeholder = "(" + ', '.join('?' * len(keys)) + ")"

        query = "UPDATE " + self._name + " SET " + keys_str + " = " + placeholder + " WHERE id = ?"

        values = [self._ENCODE_FUNCTIONS.get(k, lambda x: x)(data[k]) for k in keys]
        values.append(id_)
        values = tuple(values)

        cursor = self._connection.cursor()
        cursor.execute(query, values)

        self.Updated.emit()
