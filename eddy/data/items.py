import json

from eddy.data.database import Table


class ItemsTable(Table):
    _KEYS = {
        "id": "INTEGER PRIMARY KEY",
        "type": "TEXT",
        "date": "TEXT",
        "authors": "TEXT",
        "authors_bais": "TEXT",
        "editors": "TEXT",
        "editors_bais": "TEXT",
        "title": "TEXT",
        "abstract": "TEXT",
        "publication": "TEXT",
        "volume": "TEXT",
        "year": "INTEGER",
        "issue": "TEXT",
        "pages": "TEXT",
        "edition": "TEXT",
        "series": "TEXT",
        "publisher": "TEXT",
        "isbns": "TEXT",
        "institution": "TEXT",
        "degree": "TEXT",
        "citations": "INTEGER",
        "inspire_id": "INTEGER",
        "texkey": "TEXT",
        "arxiv_id": "TEXT",
        "dois": "TEXT",
        "urls": "TEXT",
        "notes": "TEXT",
        "files": "TEXT",
        "tags": "TEXT"
    }

    _DEFAULTS = {
        "type": None,
        "date": None,
        "authors": [],
        "authors_bais": [],
        "editors": [],
        "editors_bais": [],
        "title": None,
        "abstract": None,
        "publication": None,
        "volume": None,
        "year": None,
        "issue": None,
        "pages": None,
        "edition": None,
        "series": None,
        "publisher": None,
        "isbns": [],
        "institution": None,
        "degree": None,
        "citations": None,
        "inspire_id": None,
        "texkey": None,
        "arxiv_id": None,
        "dois": [],
        "urls": [],
        "notes": None,
        "files": [],
        "tags": []
    }

    _ENCODE_FUNCTIONS = {
        "authors": json.dumps,
        "authors_bais": json.dumps,
        "editors": json.dumps,
        "editors_bais": json.dumps,
        "isbns": json.dumps,
        "dois": json.dumps,
        "urls": json.dumps,
        "files": json.dumps,
        "tags": json.dumps
    }

    _DECODE_FUNCTIONS = {
        "authors": json.loads,
        "authors_bais": json.loads,
        "editors": json.loads,
        "editors_bais": json.loads,
        "isbns": json.loads,
        "dois": json.loads,
        "urls": json.loads,
        "files": json.loads,
        "tags": json.loads
    }

    def __init__(self, database, name="items", drop_on_del=False, parent=None):
        super(ItemsTable, self).__init__(database, name, drop_on_del, parent)

    def GetTable(self, keys, sort_key=None, sort_order="DESC", filter_strings=()):
        keys = list({k for k in keys if k in self._KEYS.keys()})
        n_strings = len(filter_strings)

        query = "SELECT " + ", ".join(keys) + " FROM " + self._name
        if n_strings > 0:
            query = query + " WHERE authors || title LIKE ?"
        if n_strings > 1:
            query = query + (" AND authors || title LIKE ?" * (n_strings - 1))
        if sort_key is not None:
            query = query + " ORDER BY " + sort_key + " " + sort_order

        patterns = tuple("%" + f + "%" for f in filter_strings)

        cursor = self._connection.cursor()
        cursor.execute(query, patterns)
        data = [dict(zip(keys, t)) for t in cursor.fetchall()]
        for k in self._DECODE_FUNCTIONS:
            if k in keys:
                for d in data:
                    d[k] = self._DECODE_FUNCTIONS[k](d[k])

        return data
