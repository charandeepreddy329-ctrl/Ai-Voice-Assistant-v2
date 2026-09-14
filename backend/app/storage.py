import json
import sqlite3
from pathlib import Path

class LocalStorage:
    """SQLite storage scoped to a server-issued visitor identity."""
    def __init__(self, path: str, session: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path, self.session = path, session
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, session TEXT, collection TEXT, payload TEXT)')
            db.execute('CREATE INDEX IF NOT EXISTS scope ON records(session, collection, id)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def append(self, collection, record):
        with self.connect() as db:
            db.execute('INSERT INTO records(session,collection,payload) VALUES(?,?,?)', (self.session, collection, json.dumps(record)))
            db.execute('DELETE FROM records WHERE session=? AND collection=? AND id NOT IN (SELECT id FROM records WHERE session=? AND collection=? ORDER BY id DESC LIMIT 100)', (self.session,collection,self.session,collection))

    def read(self, collection, limit):
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM records WHERE session=? AND collection=? ORDER BY id DESC LIMIT ?', (self.session,collection,limit)).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]

    def append_command(self, command): pass  # Do not keep redundant command logs.
    def remember(self, content): self.append('memories', {'content': content})
    def add_note(self, content): self.append('notes', {'content': content})
    def recent_memories(self, limit=5): return self.read('memories', limit)
    def recent_notes(self, limit=5): return self.read('notes', limit)
    def append_conversation(self, role, content): self.append('chat', {'role':role, 'content':content})
    def recent_conversation(self, limit=10): return self.read('chat', limit)
    def clear(self):
        with self.connect() as db: db.execute('DELETE FROM records WHERE session=?', (self.session,))
