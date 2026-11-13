"""Productivity Analytics - CustomTkinter UI. Run: python app.py"""
import calendar, re, tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox
import customtkinter as ctk
import db as dbm, logic as L

PAGES = ["Dashboard", "Calendar", "Tasks", "Habits", "Focus", "Analytics", "Settings"]
PRIO = ["Low", "Medium", "High", "Urgent"]

class Form(ctk.CTkToplevel):
    """Generic modal form. fields: [(key, label, default)]; on_save(values) may raise ValueError."""
    def __init__(self, app, title, fields, on_save, on_delete=None):
        super().__init__(app); self.title(title); self.geometry("380x%d" % (90 + 56 * len(fields) + (40 if on_delete else 0)))
        self.transient(app); self.after(100, self.grab_set); self.e = {}
        for k, label, default in fields:
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=20, pady=(8, 0))
            if isinstance(default, list):
                w = ctk.CTkOptionMenu(self, values=default); w.set(default[0])
            else:
                w = ctk.CTkEntry(self); w.insert(0, str(default))
            w.pack(fill="x", padx=20); self.e[k] = w
        def save():
            try: on_save({k: w.get() for k, w in self.e.items()}); self.destroy(); app.render()
            except ValueError as ex: messagebox.showerror("Invalid input", str(ex), parent=self)
        ctk.CTkButton(self, text="Save", command=save).pack(pady=(14, 4))
        if on_delete:
            def delete():
                if on_delete() is not False: self.destroy(); app.render()
            ctk.CTkButton(self, text="Delete", fg_color="#c0392b", command=delete).pack()

class App(ctk.CTk):
    def __init__(self):
        super().__init__(); self.db = dbm.DB(); L.seed_defaults(self.db)
        ctk.set_appearance_mode(L.get_setting(self.db, "theme"))
        self.title("Productivity Analytics"); self.geometry("1150x740"); self.minsize(900, 600)
        self.page, self.month, self.task_filter = "Dashboard", date.today().replace(day=1), "Today"
        self.sel_day = date.today(); self.timer = {"left": 0, "run": False, "mode": "Work"}
        side = self.side = ctk.CTkFrame(self, width=int(L.get_setting(self.db, "sidebar_width")), corner_radius=0); side.pack_propagate(False)
        ctk.CTkLabel(side, text="Productivity\nAnalytics", font=("", 18, "bold")).pack(pady=24)
        for p in PAGES: ctk.CTkButton(side, text=p, anchor="w", fg_color="transparent", text_color=("gray10", "gray90"),
                                      hover_color=("gray80", "gray25"), command=lambda p=p: self.go(p)).pack(fill="x", padx=10, pady=2)
        self.grip = ctk.CTkFrame(self, width=5, corner_radius=0, fg_color=("gray75", "gray30"))
        self.grip.bind("<Enter>", lambda e: self.configure(cursor="sb_h_double_arrow")); self.grip.bind("<Leave>", lambda e: self.configure(cursor=""))
        self.grip.bind("<B1-Motion>", self.resize_side)
        self.grip.bind("<ButtonRelease-1>", lambda e: L.set_setting(self.db, "sidebar_width", self.side.cget("width")))
        self.right = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkButton(self.right, text="☰", width=36, command=self.toggle_side).pack(anchor="w", padx=16, pady=(10, 0))
        self.main = ctk.CTkFrame(self.right, fg_color="transparent"); self.main.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        if L.get_setting(self.db, "sidebar_hidden") == "0": self.side.pack(side="left", fill="y"); self.grip.pack(side="left", fill="y")
        self.right.pack(side="left", fill="both", expand=True)
        self.render()

    def resize_side(self, e):
        self.side.configure(width=max(120, min(320, e.x_root - self.side.winfo_rootx())))
    def toggle_side(self):
        if self.side.winfo_ismapped(): self.side.pack_forget(); self.grip.pack_forget(); hidden = "1"
        else: self.side.pack(side="left", fill="y", before=self.right); self.grip.pack(side="left", fill="y", before=self.right); hidden = "0"
        L.set_setting(self.db, "sidebar_hidden", hidden)

    def go(self, p): self.page = p; self.render()
    def render(self):
        for w in self.main.winfo_children(): w.destroy()
        ctk.CTkLabel(self.main, text=self.page, font=("", 24, "bold")).pack(anchor="w", pady=(0, 8))
        try: getattr(self, "p_" + self.page.lower())()
        except Exception as ex: messagebox.showerror("Error", str(ex))

    def card(self, parent, title):
        c = ctk.CTkFrame(parent, corner_radius=12); ctk.CTkLabel(c, text=title, font=("", 14, "bold")).pack(anchor="w", padx=14, pady=(10, 4)); return c
    def scroll(self): s = ctk.CTkScrollableFrame(self.main); s.pack(fill="both", expand=True); return s
    def lbl(self, p, t, **k): ctk.CTkLabel(p, text=t, anchor="w", justify="left", **k).pack(fill="x", padx=14, pady=1)

    # ---- Dashboard
    def p_dashboard(self):
        db, t = self.db, date.today(); h = datetime.now().hour
        self.lbl(self.main, f"Good {'morning' if h < 12 else 'afternoon' if h < 18 else 'evening'} - {t.strftime('%A, %d %B %Y')}", font=("", 15))
        row = ctk.CTkFrame(self.main, fg_color="transparent"); row.pack(fill="x", pady=6)
        for txt, cmd in [("+ Task", self.new_task), ("+ Event", lambda: self.event_form(t)), ("+ Habit", self.new_habit)]:
            ctk.CTkButton(row, text=txt, width=90, command=cmd).pack(side="left", padx=4)
        grid = ctk.CTkFrame(self.main, fg_color="transparent"); grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1)
        c = self.card(grid, "Productivity score"); c.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(c, text=f"{L.productivity_score(db)}%", font=("", 40, "bold")).pack(pady=6)
        c = self.card(grid, "Schedule today"); c.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        for e in L.events_on(db, t) or [None]:
            self.lbl(c, "Nothing scheduled" if not e else f"{'All day' if e['all_day'] else L.fmt_time(db, e['start'])}  {e['title']}", text_color=e and e["color"])
        c = self.card(grid, "Tasks due / overdue"); c.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        ts = db.q("SELECT * FROM tasks WHERE status!='done' AND due<=? ORDER BY due", (L.iso(t),))
        for x in ts or [None]: self.lbl(c, "All clear" if not x else f"{'OVERDUE ' if x['due'] < L.iso(t) else ''}{x['title']}")
        c = self.card(grid, "Habits today"); c.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        hs = db.q("SELECT * FROM habits WHERE archived=0")
        for x in hs or [None]:
            v = db.q("SELECT value FROM habit_logs WHERE habit_id=? AND day=?", (x["id"], L.iso(t))) if x else []
            self.lbl(c, "No habits yet" if not x else f"{'✓' if v and L.habit_done(x, v[0]['value']) else '○'} {x['name']}")

    # ---- Calendar
    def p_calendar(self):
        db = self.db; bar = ctk.CTkFrame(self.main, fg_color="transparent"); bar.pack(fill="x")
        def shift(n): m = self.month.month - 1 + n; self.month = date(self.month.year + m // 12, m % 12 + 1, 1); self.render()
        ctk.CTkButton(bar, text="<", width=36, command=lambda: shift(-1)).pack(side="left")
        ctk.CTkLabel(bar, text=self.month.strftime("%B %Y"), font=("", 16, "bold"), width=160).pack(side="left")
        ctk.CTkButton(bar, text=">", width=36, command=lambda: shift(1)).pack(side="left")
        ctk.CTkButton(bar, text="+ Event", width=80, command=lambda: self.event_form(self.sel_day)).pack(side="right")
        ctk.CTkButton(bar, text="+ Calendar", width=90, command=self.calendar_form).pack(side="right", padx=6)
        body = ctk.CTkFrame(self.main, fg_color="transparent"); body.pack(fill="both", expand=True, pady=6)
        side = ctk.CTkFrame(body, width=170); side.pack(side="left", fill="y", padx=(0, 8))
        self.lbl(side, "Calendars", font=("", 13, "bold"))
        for cal in db.q("SELECT * FROM calendars"):
            v = tk.IntVar(value=cal["visible"])
            r = ctk.CTkFrame(side, fg_color="transparent"); r.pack(fill="x")
            ctk.CTkCheckBox(r, text=cal["name"], variable=v, fg_color=cal["color"], width=20,
                            command=lambda c=cal, v=v: (db.x("UPDATE calendars SET visible=? WHERE id=?", (v.get(), c["id"])), self.render())).pack(side="left", padx=(10, 0), pady=3)
            ctk.CTkButton(r, text="✎", width=24, fg_color="transparent", command=lambda c=cal: self.calendar_form(c)).pack(side="right")
        grid = ctk.CTkFrame(body); grid.pack(side="left", fill="both", expand=True)
        ws = {"Monday": 0, "Saturday": 5, "Sunday": 6}[L.get_setting(db, "week_start")]
        cal = calendar.Calendar(ws)
        for i, d in enumerate(cal.iterweekdays()): ctk.CTkLabel(grid, text=calendar.day_abbr[d]).grid(row=0, column=i)
        weeks = cal.monthdatescalendar(self.month.year, self.month.month)
        for r, wk in enumerate(weeks, 1):
            grid.rowconfigure(r, weight=1)
            for i, d in enumerate(wk):
                grid.columnconfigure(i, weight=1)
                cell = ctk.CTkFrame(grid, border_width=2 if d == self.sel_day else 1, corner_radius=6,
                                    border_color=("#3b82f6" if d == self.sel_day else ("gray70", "gray30")))
                cell.grid(row=r, column=i, sticky="nsew", padx=1, pady=1)
                ctk.CTkLabel(cell, text=str(d.day), anchor="w", text_color=("gray10", "gray90") if d.month == self.month.month else "gray50").pack(fill="x", padx=4)
                for e in L.events_on(db, d)[:3]:
                    b = ctk.CTkLabel(cell, text=e["title"], fg_color=e["color"], text_color="white", corner_radius=4, font=("", 10), anchor="w")
                    b.pack(fill="x", padx=3, pady=1); b.bind("<Button-1>", lambda ev, e=e: self.event_form(L.parse_date(e["day"]), e))
                cell.bind("<Button-1>", lambda ev, d=d: self.pick(d))
                for w in cell.winfo_children()[:1]: w.bind("<Button-1>", lambda ev, d=d: self.pick(d))
    def pick(self, d): self.sel_day = d; self.render()

    def calendar_form(self, cal=None):
        """Create a calendar, or edit/delete an existing one (its events are deleted with it)."""
        db, cal = self.db, cal or {}
        def save(v):
            name, color = v["name"].strip(), v["color"].strip()
            if not name: raise ValueError("Name required")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color): raise ValueError("Color must look like #8b5cf6")
            if cal: db.x("UPDATE calendars SET name=?,color=?,description=? WHERE id=?", (name, color, v["description"], cal["id"]))
            else: db.x("INSERT INTO calendars(name,color,description) VALUES(?,?,?)", (name, color, v["description"]))
        def delete():
            if db.q("SELECT COUNT(*) n FROM calendars")[0]["n"] < 2:
                messagebox.showerror("Cannot delete", "At least one calendar must remain."); return False
            n = db.q("SELECT COUNT(*) n FROM events WHERE calendar_id=?", (cal["id"],))[0]["n"]
            if not messagebox.askyesno("Delete calendar", f"Delete '{cal['name']}' and its {n} event(s)? This cannot be undone."): return False
            db.x("DELETE FROM calendars WHERE id=?", (cal["id"],))
        Form(self, "Edit calendar" if cal else "New calendar", [("name", "Name", cal.get("name", "")), ("color", "Color (hex)", cal.get("color", "#8b5cf6")),
             ("description", "Description", cal.get("description", ""))], save, delete if cal else None)

    def event_form(self, day, ev=None):
        cals = self.db.q("SELECT id,name FROM calendars"); names = [c["name"] for c in cals]
        ev = ev or {}; cur = next((c["name"] for c in cals if c["id"] == ev.get("calendar_id")), names[0])
        def save(v):
            v["all_day"] = int(v["all_day"] in ("yes", "1")); L.validate_event(v)
            cid = next(c["id"] for c in cals if c["name"] == v["calendar"])
            args = (cid, v["title"].strip(), v["description"], v["location"], v["day"], L.parse_time(v["start"]), L.parse_time(v["end"]), v["all_day"], v["recurrence"])
            if ev: self.db.x("UPDATE events SET calendar_id=?,title=?,description=?,location=?,day=?,start=?,end=?,all_day=?,recurrence=? WHERE id=?", args + (ev["id"],))
            else: self.db.x("INSERT INTO events(calendar_id,title,description,location,day,start,end,all_day,recurrence) VALUES(?,?,?,?,?,?,?,?,?)", args)
        Form(self, "Event", [("title", "Title", ev.get("title", "")), ("calendar", "Calendar", [cur] + [n for n in names if n != cur]),
             ("day", "Date (YYYY-MM-DD)", ev.get("day", L.iso(day))), ("start", "Start (HH:MM)", ev.get("start", "09:00")), ("end", "End (HH:MM)", ev.get("end", "10:00")),
             ("all_day", "All day", ["no", "yes"]), ("recurrence", "Repeat", [ev.get("recurrence", "none")] + [r for r in ["none", "daily", "weekly", "monthly", "yearly"] if r != ev.get("recurrence", "none")]),
             ("location", "Location", ev.get("location", "")), ("description", "Description", ev.get("description", ""))], save,
             (lambda: self.db.x("DELETE FROM events WHERE id=?", (ev["id"],))) if ev else None)

    # ---- Tasks
    def p_tasks(self):
        db, t = self.db, L.iso(date.today())
        seg = ctk.CTkSegmentedButton(self.main, values=["Inbox", "Today", "Upcoming", "All", "Overdue", "Completed"], command=lambda v: (setattr(self, "task_filter", v), self.render()))
        seg.set(self.task_filter); seg.pack(anchor="w"); ctk.CTkButton(self.main, text="+ Task", width=80, command=self.new_task).pack(anchor="e")
        where = {"Inbox": ("project_id IS NULL AND status!='done'", ()), "Today": ("due=? AND status!='done'", (t,)), "Upcoming": ("due>? AND status!='done'", (t,)),
                 "All": ("1", ()), "Overdue": ("due<? AND status!='done'", (t,)), "Completed": ("status='done'", ())}[self.task_filter]
        s = self.scroll()
        for x in db.q(f"SELECT t.*, p.name pn FROM tasks t LEFT JOIN projects p ON p.id=t.project_id WHERE {where[0]} ORDER BY priority DESC, due", where[1]) or [None]:
            if not x: self.lbl(s, "No tasks here"); continue
            r = ctk.CTkFrame(s); r.pack(fill="x", pady=2); v = tk.IntVar(value=x["status"] == "done")
            ctk.CTkCheckBox(r, text=f"{x['title']}  [{PRIO[x['priority']]}] {x['due'] or ''} {('· ' + x['pn']) if x['pn'] else ''}", variable=v, command=lambda x=x, v=v: (
                db.x("UPDATE tasks SET status=?, done_on=? WHERE id=?", ("done" if v.get() else "todo", t if v.get() else None, x["id"])), self.render())).pack(side="left", padx=8, pady=6)
            ctk.CTkButton(r, text="✕", width=28, fg_color="transparent", command=lambda x=x: (db.x("DELETE FROM tasks WHERE id=?", (x["id"],)), self.render())).pack(side="right")
    def new_task(self):
        projs = self.db.q("SELECT id,name FROM projects")
        def save(v):
            if not v["title"].strip(): raise ValueError("Title is required")
            if v["due"].strip(): L.parse_date(v["due"])
            pid = next((p["id"] for p in projs if p["name"] == v["project"]), None)
            self.db.x("INSERT INTO tasks(title,due,priority,est_min,project_id) VALUES(?,?,?,?,?)",
                      (v["title"].strip(), v["due"].strip() or None, PRIO.index(v["priority"]), int(v["est"] or 0), pid))
        Form(self, "New task", [("title", "Title", ""), ("due", "Due (YYYY-MM-DD, optional)", ""), ("priority", "Priority", PRIO),
             ("est", "Estimated minutes", "0"), ("project", "Project", ["(none)"] + [p["name"] for p in projs])], save)

    # ---- Habits
    def p_habits(self):
        db, t = self.db, L.iso(date.today()); ctk.CTkButton(self.main, text="+ Habit", width=80, command=self.new_habit).pack(anchor="e"); s = self.scroll()
        for h in db.q("SELECT * FROM habits WHERE archived=0") or [None]:
            if not h: self.lbl(s, "No habits yet"); continue
            r = db.q("SELECT value FROM habit_logs WHERE habit_id=? AND day=?", (h["id"], t)); val = r[0]["value"] if r else 0
            cur, best = L.streaks(db, h); row = ctk.CTkFrame(s); row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{h['name']}  ({val:g}/{h['target']:g})  streak {cur} · best {best} · 30d {L.habit_rate(db, h):.0%}").pack(side="left", padx=10, pady=8)
            ctk.CTkButton(row, text="✕", width=28, fg_color="transparent", command=lambda h=h: (db.x("UPDATE habits SET archived=1 WHERE id=?", (h["id"],)), self.render())).pack(side="right")
            if h["kind"] == "yesno":
                ctk.CTkButton(row, text="Undo" if val else "Done", width=70, command=lambda h=h, v=val: self.log(h, 0 if v else 1)).pack(side="right")
            else:
                e = ctk.CTkEntry(row, width=60); e.pack(side="right", padx=4)
                ctk.CTkButton(row, text="Log", width=50, command=lambda h=h, e=e: self.log(h, e.get())).pack(side="right")
    def log(self, h, v):
        try: v = float(v)
        except ValueError: return messagebox.showerror("Invalid", "Enter a number")
        self.db.x("INSERT OR REPLACE INTO habit_logs VALUES(?,?,?)", (h["id"], L.iso(date.today()), v)); self.render()
    def new_habit(self):
        def save(v):
            if not v["name"].strip(): raise ValueError("Name required")
            self.db.x("INSERT INTO habits(name,kind,target) VALUES(?,?,?)", (v["name"].strip(), v["kind"], float(v["target"] or 1)))
        Form(self, "New habit", [("name", "Name", ""), ("kind", "Type", ["yesno", "number", "duration"]), ("target", "Daily target (number / minutes)", "1")], save)

    # ---- Focus (Pomodoro)
    def p_focus(self):
        f = ctk.CTkFrame(self.main); f.pack(pady=20, padx=20)
        w, b = ctk.CTkEntry(f, width=60), ctk.CTkEntry(f, width=60); w.insert(0, "25"); b.insert(0, "5")
        ctk.CTkLabel(f, text="Work min").grid(row=0, column=0, padx=6); w.grid(row=0, column=1); ctk.CTkLabel(f, text="Break min").grid(row=0, column=2, padx=6); b.grid(row=0, column=3)
        self.clock = ctk.CTkLabel(self.main, text="--:--", font=("", 64, "bold")); self.clock.pack(pady=10)
        def start():
            try: self.timer.update(left=int(w.get()) * 60, run=True, mode="Work", w=int(w.get()), b=int(b.get()))
            except ValueError: return messagebox.showerror("Invalid", "Minutes must be whole numbers")
            self.tick()
        ctk.CTkButton(self.main, text="Start", command=start).pack(); ctk.CTkButton(self.main, text="Stop", fg_color="gray40", command=lambda: self.timer.update(run=False)).pack(pady=4)
        m = self.db.q("SELECT COALESCE(SUM(minutes),0) n FROM focus_sessions WHERE day=?", (L.iso(date.today()),))[0]["n"]
        self.lbl(self.main, f"Focus time today: {m} min", font=("", 14))
    def tick(self):
        T = self.timer
        if not T["run"] or not self.clock.winfo_exists(): return
        T["left"] -= 1
        if T["left"] < 0:
            if T["mode"] == "Work": self.db.x("INSERT INTO focus_sessions(day,minutes) VALUES(?,?)", (L.iso(date.today()), T["w"]))
            T["mode"] = "Break" if T["mode"] == "Work" else "Work"; T["left"] = 60 * T["b" if T["mode"] == "Break" else "w"]; self.bell()
        self.clock.configure(text=f"{T['mode']} {T['left'] // 60:02d}:{T['left'] % 60:02d}"); self.after(1000, self.tick)

    # ---- Analytics
    def p_analytics(self):
        import matplotlib; matplotlib.use("TkAgg")
        from matplotlib.figure import Figure; from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        dark = ctk.get_appearance_mode() == "Dark"; fg, bg = ("#e5e7eb", "#2b2b2b") if dark else ("#111827", "#ebebeb")
        fig = Figure(figsize=(9, 5), facecolor=bg)
        data = [("Tasks completed", "SELECT COUNT(*) n FROM tasks WHERE done_on=?"), ("Focus minutes", "SELECT SUM(minutes) n FROM focus_sessions WHERE day=?"),
                ("Habit check-ins", "SELECT COUNT(*) n FROM habit_logs WHERE day=?")]
        for i, (title, sql) in enumerate(data, 1):
            ax = fig.add_subplot(3, 1, i, facecolor=bg); x, y = L.daily_series(self.db, sql)
            ax.bar(x, y, color="#4f8cff"); ax.set_title(title, color=fg, fontsize=10, loc="left"); ax.tick_params(colors=fg, labelsize=8)
            for sp in ax.spines.values(): sp.set_color(fg)
        fig.tight_layout(); c = FigureCanvasTkAgg(fig, self.main); c.get_tk_widget().pack(fill="both", expand=True)

    # ---- Settings
    def p_settings(self):
        db = self.db; f = ctk.CTkFrame(self.main); f.pack(fill="x", padx=4)
        for i, (k, label, vals) in enumerate([("theme", "Theme", ["dark", "light"]), ("week_start", "Week starts on", ["Monday", "Sunday", "Saturday"]), ("time_format", "Time format (12/24)", ["24", "12"])]):
            ctk.CTkLabel(f, text=label).grid(row=i, column=0, padx=14, pady=10, sticky="w")
            m = ctk.CTkOptionMenu(f, values=vals, command=lambda v, k=k: self.setopt(k, v)); m.set(L.get_setting(db, k)); m.grid(row=i, column=1)
        row = ctk.CTkFrame(self.main, fg_color="transparent"); row.pack(anchor="w", pady=14)
        ctk.CTkButton(row, text="Export backup", command=self.do_export).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Restore backup", command=self.do_restore).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Load demo data", fg_color="gray40", command=lambda: (L.load_demo(db), self.render())).pack(side="left", padx=4)
    def setopt(self, k, v):
        L.set_setting(self.db, k, v)
        if k == "theme": ctk.set_appearance_mode(v)
        self.render()
    def do_export(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="productivity_backup.json")
        if p: self.db.export(p); messagebox.showinfo("Backup", "Backup saved.")
    def do_restore(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p and messagebox.askyesno("Restore", "This replaces all current data. Continue?"):
            try: self.db.restore(p); L.seed_defaults(self.db); self.render()
            except (ValueError, OSError) as e: messagebox.showerror("Restore failed", str(e))

if __name__ == "__main__":
    App().mainloop()
