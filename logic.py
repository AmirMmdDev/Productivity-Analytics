"""Business logic: settings, recurring events, streaks, scores, demo data."""
from datetime import date, datetime, timedelta

ISO = "%Y-%m-%d"
def iso(d): return d.strftime(ISO)
def parse_date(s): return datetime.strptime(s.strip(), ISO).date()
def parse_time(s): return datetime.strptime(s.strip(), "%H:%M").strftime("%H:%M")

DEFAULTS = {"theme": "dark", "week_start": "Monday", "time_format": "24", "default_calendar": "1", "sidebar_width": "180", "sidebar_hidden": "0"}
def get_setting(db, k):
    r = db.q("SELECT v FROM settings WHERE k=?", (k,))
    return r[0]["v"] if r else DEFAULTS[k]
def set_setting(db, k, v): db.x("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, str(v)))
def fmt_time(db, t): return t if get_setting(db, "time_format") == "24" else datetime.strptime(t, "%H:%M").strftime("%I:%M %p")

def _occurs(ev, day):
    start = parse_date(ev["day"])
    if day < start: return False
    r = ev["recurrence"]
    return (r == "none" and day == start) or r == "daily" or \
        (r == "weekly" and (day - start).days % 7 == 0) or \
        (r == "monthly" and day.day == start.day) or (r == "yearly" and (day.month, day.day) == (start.month, start.day))

def events_on(db, day, visible_only=True):
    sql = "SELECT e.*, c.color, c.name AS cal FROM events e JOIN calendars c ON c.id=e.calendar_id" + (" WHERE c.visible=1" if visible_only else "")
    return sorted((e for e in db.q(sql) if _occurs(e, day)), key=lambda e: (-e["all_day"], e["start"]))

def validate_event(f):
    if not f["title"].strip(): raise ValueError("Title is required")
    parse_date(f["day"]); s, e = parse_time(f["start"]), parse_time(f["end"])
    if e < s: raise ValueError("End time is before start time")

def habit_done(h, value): return value is not None and value >= h["target"]
def streaks(db, h):
    logs = {r["day"]: r["value"] for r in db.q("SELECT day,value FROM habit_logs WHERE habit_id=?", (h["id"],))}
    ok = {parse_date(d) for d, v in logs.items() if habit_done(h, v)}
    d = date.today() if date.today() in ok else date.today() - timedelta(1)
    cur = 0
    while d in ok: cur += 1; d -= timedelta(1)
    best = run = 0
    for d in sorted(ok):
        run = run + 1 if d - timedelta(1) in ok else 1; best = max(best, run)
    return cur, best

def habit_rate(db, h, days=30):
    since = iso(date.today() - timedelta(days - 1))
    n = db.q("SELECT COUNT(*) n FROM habit_logs WHERE habit_id=? AND day>=? AND value>=?", (h["id"], since, h["target"]))[0]["n"]
    return n / days

def productivity_score(db, day=None):
    day = iso(day or date.today())
    tasks = db.q("SELECT status FROM tasks WHERE due=?", (day,))
    habits = db.q("SELECT * FROM habits WHERE archived=0")
    t = (sum(x["status"] == "done" for x in tasks) / len(tasks)) if tasks else None
    done = sum(habit_done(h, (db.q("SELECT value FROM habit_logs WHERE habit_id=? AND day=?", (h["id"], day)) or [{"value": None}])[0]["value"]) for h in habits)
    h = done / len(habits) if habits else None
    parts = [p for p in (t, h) if p is not None]
    return round(100 * sum(parts) / len(parts)) if parts else 0

def daily_series(db, sql, days=14):
    """Return (labels, values) for the last N days; sql takes a day param and returns one number."""
    ds = [date.today() - timedelta(i) for i in range(days - 1, -1, -1)]
    return [d.strftime("%d/%m") for d in ds], [db.q(sql, (iso(d),))[0]["n"] or 0 for d in ds]

def seed_defaults(db):
    if not db.q("SELECT 1 FROM calendars"):
        for n, c in [("Personal", "#4f8cff"), ("Work", "#f59e0b"), ("Study", "#10b981"), ("Exercise", "#ef4444")]:
            db.x("INSERT INTO calendars(name,color) VALUES(?,?)", (n, c))

def load_demo(db):
    seed_defaults(db); t = date.today()
    db.x("INSERT INTO projects(name,area) VALUES('Thesis','Education')")
    for title, off, p in [("Write intro", 0, 2), ("Pay bills", -1, 3), ("Plan trip", 3, 0)]:
        db.x("INSERT INTO tasks(title,due,priority,project_id,est_min) VALUES(?,?,?,1,45)", (title, iso(t + timedelta(off)), p))
    db.x("INSERT INTO events(calendar_id,title,day,start,end,recurrence) VALUES(2,'Standup',?, '09:30','09:45','daily')", (iso(t),))
    db.x("INSERT INTO events(calendar_id,title,day,start,end) VALUES(3,'Study group',?, '17:00','19:00')", (iso(t),))
    for n, k, tg in [("Meditate", "yesno", 1), ("Read pages", "number", 30), ("Study (min)", "duration", 120)]:
        hid = db.x("INSERT INTO habits(name,kind,target) VALUES(?,?,?)", (n, k, tg))
        for i in range(1, 6): db.x("INSERT INTO habit_logs VALUES(?,?,?)", (hid, iso(t - timedelta(i)), tg))
