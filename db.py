"""SQLite persistence layer: schema, queries, export/import."""
import json, sqlite3
from pathlib import Path

PATH = Path.home() / ".productivity_analytics.db"
TABLES = ["calendars", "events", "projects", "tasks", "habits", "habit_logs", "focus_sessions", "settings"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS calendars(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, color TEXT NOT NULL, description TEXT DEFAULT '', visible INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, calendar_id INTEGER NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  title TEXT NOT NULL, description TEXT DEFAULT '', location TEXT DEFAULT '', day TEXT NOT NULL, start TEXT DEFAULT '09:00', end TEXT DEFAULT '10:00',
  all_day INTEGER DEFAULT 0, recurrence TEXT DEFAULT 'none');
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, area TEXT DEFAULT 'Personal', deadline TEXT);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '', due TEXT, priority INTEGER DEFAULT 1,
  status TEXT DEFAULT 'todo', project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL, est_min INTEGER DEFAULT 0, spent_min INTEGER DEFAULT 0, done_on TEXT);
CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY, name TEXT NOT NULL, color TEXT DEFAULT '#4f8cff', kind TEXT DEFAULT 'yesno', target REAL DEFAULT 1, archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS habit_logs(habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE, day TEXT, value REAL, PRIMARY KEY(habit_id, day));
CREATE TABLE IF NOT EXISTS focus_sessions(id INTEGER PRIMARY KEY, day TEXT, minutes INTEGER);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
"""

class DB:
    def __init__(self, path=PATH):
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys=ON")
        self.c.executescript(SCHEMA)
        self.c.commit()

    def q(self, sql, a=()):
        return [dict(r) for r in self.c.execute(sql, a)]

    def x(self, sql, a=()):
        """Execute a write; commits immediately (automatic saving)."""
        try:
            cur = self.c.execute(sql, a); self.c.commit(); return cur.lastrowid
        except sqlite3.Error as e:
            self.c.rollback(); raise ValueError(f"Database error: {e}")

    def export(self, path):
        Path(path).write_text(json.dumps({t: self.q(f"SELECT * FROM {t}") for t in TABLES}, indent=1))

    def restore(self, path):
        data = json.loads(Path(path).read_text())
        try:
            for t in reversed(TABLES): self.c.execute(f"DELETE FROM {t}")
            for t in TABLES:
                for r in data.get(t, []):
                    cols = ",".join(r); ph = ",".join("?" * len(r))
                    self.c.execute(f"INSERT INTO {t}({cols}) VALUES({ph})", list(r.values()))
            self.c.commit()
        except (sqlite3.Error, AttributeError) as e:
            self.c.rollback(); raise ValueError(f"Invalid backup: {e}")
