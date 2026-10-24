"""Disk-backed spreadsheet browsing; never return or retain a whole file in RAM."""
import json
import sqlite3
from contextlib import closing


class GridIndex:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA cache_size=-4096')
        self.db.execute('CREATE TABLE rows (sheet TEXT, number INTEGER, cells TEXT, refs TEXT, PRIMARY KEY(sheet,number)) WITHOUT ROWID')
        self.db.execute('CREATE TABLE strings (id INTEGER PRIMARY KEY, value TEXT)')
        self.pending = 0

    def row(self, sheet, number, cells, refs=None):
        self.db.execute('INSERT INTO rows VALUES (?,?,?,?)', (sheet, number, json.dumps(cells), json.dumps(refs or {})))
        self.pending += 1
        if self.pending % 1000 == 0:
            self.db.commit()

    def string(self, identifier, value):
        self.db.execute('INSERT INTO strings VALUES (?,?)', (identifier, value[:500]))

    def close(self, commit=True):
        db, self.db = self.db, None
        if db is None:
            return
        try:
            if commit:
                db.commit()
        finally:
            db.close()


def read_rows(path, strings_path, sheet, offset, limit, column, columns):
    # Read-only connections cannot accidentally recreate deleted/expired indexes.
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db, closing(sqlite3.connect(strings_path.as_uri()+'?mode=ro', uri=True)) as strings:
        result, cache = [], {}
        for number, cells, refs in db.execute('SELECT number,cells,refs FROM rows WHERE sheet=? ORDER BY number LIMIT ? OFFSET ?', (sheet, limit, offset)):
            values, references = json.loads(cells), json.loads(refs)
            row = []
            for index in range(column, min(column+20, columns)):
                key = str(index)
                if key in references:
                    identifier = references[key]
                    if identifier not in cache:
                        found = strings.execute('SELECT value FROM strings WHERE id=?', (identifier,)).fetchone()
                        if found is None:
                            raise ValueError('Missing worksheet shared string')
                        cache[identifier] = found[0]
                    row.append(cache[identifier])
                else:
                    row.append(values.get(key, ''))
            result.append({'row_number': number, 'values': row})
        return result
