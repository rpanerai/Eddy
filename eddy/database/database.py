import sqlite3
from pathlib import Path

from PySide2.QtCore import QObject, Signal


class Database(QObject):
    def __init__(self, file=":memory:", parent=None):
        super().__init__(parent)

        match file:
            case ":memory:":
                self.file = ":memory:"
            case str():
                self.file = Path(file).resolve()
            case Path():
                self.file = file.resolve()

        self.connection = sqlite3.connect(self.file, isolation_level=None)

    def __del__(self):
        self.connection.close()
        print(f"Closing connection to database '{self.file}'")


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
        self._name = name
        self._drop_on_del = drop_on_del

    def __del__(self):
        if self._drop_on_del:
            try:
                cursor = self.Cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {self._name}")
                print(f"Dropping table '{self._name}'")
            except sqlite3.ProgrammingError:
                # If the database connection has already been closed, we simply ignore this step.
                pass

    def Cursor(self):
        return self.database.connection.cursor()

    def Clear(self):
        cursor = self.Cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {self._name}")

        keys = ", ".join([f"{k} {t}" for k, t in self._KEYS.items()])
        cursor.execute(f"CREATE TABLE {self._name} ({keys})")

        self.Cleared.emit()

    def AddData(self, data):
        keys = self._DEFAULTS.keys()

        keys_str = f"({', '.join(keys)})"
        placeholder = f"({', '.join('?' * len(keys))})"
        query = f"INSERT INTO {self._name}{keys_str} VALUES {placeholder}"
        values = [
            tuple(
                self._ENCODE_FUNCTIONS.get(k, lambda x: x)(d.get(k, self._DEFAULTS[k]))
                for k in keys
            )
            for d in data
        ]

        cursor = self.Cursor()

        # To get a valid lastrowid, we need to call execute() rather than executemany().
        if len(values) == 1:
            cursor.execute(query, values[0])
        else:
            cursor.executemany(query, values)

        self.Updated.emit()
        return cursor.lastrowid

    def Delete(self, ids):
        query = f"DELETE FROM {self._name} WHERE id = ?"
        ids = [(i,) for i in ids]

        cursor = self.Cursor()
        cursor.executemany(query, ids)

        self.Updated.emit()

    def GetRow(self, id_, keys=None):
        if keys is None:
            keys_ = self._DEFAULTS.keys()
        else:
            keys_ = list({k for k in keys if k in self._DEFAULTS.keys()})

        query = f"SELECT {', '.join(keys_)} FROM {self._name} WHERE id = {id_}"

        cursor = self.Cursor()
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

        query = f"SELECT {', '.join(keys_)} FROM {self._name}"

        cursor = self.Cursor()
        cursor.execute(query)
        data = [dict(zip(keys_, t)) for t in cursor.fetchall()]
        for k in self._DECODE_FUNCTIONS:
            if k in keys_:
                for d in data:
                    d[k] = self._DECODE_FUNCTIONS[k](d[k])

        return data

    def EditRow(self, id_, data):
        keys = [k for k in data.keys() if k in self._DEFAULTS.keys()]

        keys_str = f"({', '.join(keys)})"
        placeholder = f"({', '.join('?' * len(keys))})"

        query = f"UPDATE {self._name} SET {keys_str} = {placeholder} WHERE id = ?"

        values = [self._ENCODE_FUNCTIONS.get(k, lambda x: x)(data[k]) for k in keys]
        values.append(id_)
        values = tuple(values)

        cursor = self.Cursor()
        cursor.execute(query, values)

        self.Updated.emit()
