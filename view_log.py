from dotenv import load_dotenv
load_dotenv()

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import pandas as pd

from db import get_db_connection

PAGE_SIZE = 50


class ViewLogFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self.BASE_DIR = os.path.dirname(__file__)
        self.IMAGE_DIR = os.path.join(self.BASE_DIR, "images")

        self.scale_x = max(self.winfo_screenwidth() / 1920, 0.8)
        self.scale_y = max(self.winfo_screenheight() / 1080, 0.8)
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.current_page = 1
        self.total_pages = 1
        self.df = pd.DataFrame()

        self.build_ui()
        self.after(0, self.fetch_data)

    # ---------- UI helpers ----------
    def load_icon(self, name, size):
        path = os.path.join(self.IMAGE_DIR, name)
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def add_placeholder(self, e, t):
        e.insert(0, t); e.config(fg="grey")
        def _in(_):
            if e.get() == t:
                e.delete(0, 'end'); e.config(fg="black")
        def _out(_):
            if not e.get():
                e.insert(0, t); e.config(fg="grey")
        e.bind("<FocusIn>", _in)
        e.bind("<FocusOut>", _out)

    def colored_btn(self, parent, txt, color, cmd, hover=None, width=12, height=2):
        b = tk.Label(parent, text=txt, bg=color, fg="white",
                     font=("Segoe UI", 12, "bold"),
                     width=width, height=height, cursor="hand2")
        if hover:
            b.bind("<Enter>", lambda e: b.config(bg=hover))
            b.bind("<Leave>", lambda e: b.config(bg=color))
        b.bind("<Button-1>", lambda e: cmd())
        return b

    # ---------- Build UI ----------
    def build_ui(self):
        tk.Label(self, text="Scrap Logs",
                 font=("Segoe UI", int(36 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").pack(pady=int(20 * self.scale_y))

        # calendar icon (fallback to emoji if missing)
        try:
            self.calendar_icon = self.load_icon("schedule.png", (int(20*self.scale_x), int(20*self.scale_y)))
        except Exception:
            self.calendar_icon = None

        filt = tk.Frame(self, bg="#F8FAFC"); filt.pack(pady=int(5*self.scale_y))

        tk.Label(filt, text="Machine Operator:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=4, sticky="e")
        self.op_entry = tk.Entry(filt, font=("Segoe UI", 12), width=18, bg="white", relief="flat",
                                 highlightthickness=1, highlightbackground="#E5E7EB", highlightcolor="#3E84FB")
        self.op_entry.grid(row=0, column=1, padx=4)
        self.add_placeholder(self.op_entry, "Search Operator")
        self.op_entry.bind("<KeyRelease>", lambda e: self._delayed())

        tk.Label(filt, text="Shift:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=2, padx=12, sticky="e")
        self.shift_combo = ttk.Combobox(filt, values=["All", "A", "B", "C"],
                                        font=("Segoe UI", 12), width=6, state="readonly")
        self.shift_combo.set("All")
        self.shift_combo.grid(row=0, column=3, padx=4)
        self.shift_combo.bind("<<ComboboxSelected>>", lambda e: self.fetch_data())

        tk.Label(filt, text="From:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=4, padx=12, sticky="e")
        self.from_date = tk.Entry(filt, font=("Segoe UI", 12), width=12, bg="white", relief="flat",
                                  highlightthickness=1, highlightbackground="#E5E7EB", highlightcolor="#3E84FB")
        self.from_date.grid(row=0, column=5, padx=4)
        self.add_placeholder(self.from_date, "MM/DD/YYYY")
        self.from_date.bind("<KeyRelease>", lambda e: self._delayed())
        tk.Button(filt, image=self.calendar_icon, text=("📅" if not self.calendar_icon else ""),
                  command=lambda: self.open_calendar(self.from_date), bg="#F8FAFC", bd=0)\
            .grid(row=0, column=6, padx=3)

        tk.Label(filt, text="To:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=7, padx=12, sticky="e")
        self.to_date = tk.Entry(filt, font=("Segoe UI", 12), width=12, bg="white", relief="flat",
                                highlightthickness=1, highlightbackground="#E5E7EB", highlightcolor="#3E84FB")
        self.to_date.grid(row=0, column=8, padx=4)
        self.add_placeholder(self.to_date, "MM/DD/YYYY")
        self.to_date.bind("<KeyRelease>", lambda e: self._delayed())
        tk.Button(filt, image=self.calendar_icon, text=("📅" if not self.calendar_icon else ""),
                  command=lambda: self.open_calendar(self.to_date), bg="#F8FAFC", bd=0)\
            .grid(row=0, column=9, padx=3)

        reset_btn = self.colored_btn(filt, "Reset", "#2563EB", self.reset_filters, "#1554C9", width=8, height=1)
        reset_btn.grid(row=0, column=10, padx=(12, 4))

        table_frame = tk.Frame(self, bg="#F8FAFC"); table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # We keep 'id' in the dataframe but not as a visible column
        self.visible_cols = ("machine_operator", "machine_name", "date", "quantity", "unit",
                             "total_produced", "shift", "reason", "comments")
        self.tree = ttk.Treeview(table_frame, columns=self.visible_cols, show="headings", height=15)

        headers = {
            "machine_operator": "Operator",
            "machine_name": "Machine",
            "date": "Date",
            "quantity": "Qty",
            "unit": "Unit",
            "total_produced": "Total Produced",
            "shift": "Shift",
            "reason": "Reason",
            "comments": "Comments"
        }
        for c in self.visible_cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=int(130 * self.scale_x), anchor="center")
        self.tree.pack(fill="both", expand=True)

        action_bar = tk.Frame(self, bg="#F8FAFC"); action_bar.pack(pady=10)
        btns = tk.Frame(action_bar, bg="#F8FAFC"); btns.pack()
        self.colored_btn(btns, "Export CSV", "#2563EB", self.export, "#1554C9").pack(side="left", padx=8)
        self.colored_btn(btns, "Edit", "#22C55E", self.open_edit, "#17A34A").pack(side="left", padx=8)
        self.colored_btn(btns, "Delete", "#EF4444", self.delete_selected, "#C92C2C").pack(side="left", padx=8)

        pag = tk.Frame(self, bg="#F8FAFC"); pag.pack(pady=(0, 10))
        self.pagebar = pag

    # ---------- Filters / pagination ----------
    def reset_filters(self):
        self.op_entry.delete(0, tk.END); self.add_placeholder(self.op_entry, "Search Operator")
        self.shift_combo.set("All")
        self.from_date.delete(0, tk.END); self.add_placeholder(self.from_date, "MM/DD/YYYY")
        self.to_date.delete(0, tk.END); self.add_placeholder(self.to_date, "MM/DD/YYYY")
        self.fetch_data()

    def _delayed(self):
        if hasattr(self, "_after_id"):
            self.after_cancel(self._after_id)
        self._after_id = self.after(300, self.fetch_data)

    def open_calendar(self, entry):
        top = tk.Toplevel(self); top.title("Select Date")
        cal = Calendar(top); cal.pack(pady=10)
        def pick():
            entry.delete(0, tk.END); entry.insert(0, cal.get_date())
            top.destroy(); self.fetch_data()
        ttk.Button(top, text="Select", command=pick).pack(pady=5)

    # ---------- Data access helpers (no SQLAlchemy) ----------
    def build_query(self):
        where, params = ["1=1"], []
        op = self.op_entry.get().strip()
        if op and op != "Search Operator":
            where.append("machine_operator ILIKE %s"); params.append(f"%{op}%")
        sh = self.shift_combo.get().strip()
        if sh and sh != "All":
            where.append("shift ILIKE %s"); params.append(f"%{sh}%")
        fd = self.from_date.get().strip()
        if fd and fd != "MM/DD/YYYY":
            where.append("to_date(date,'MM/DD/YYYY') >= to_date(%s,'MM/DD/YYYY')"); params.append(fd)
        td = self.to_date.get().strip()
        if td and td != "MM/DD/YYYY":
            where.append("to_date(date,'MM/DD/YYYY') <= to_date(%s,'MM/DD/YYYY')"); params.append(td)

        sql = """
            SELECT id, machine_operator, machine_name, date, quantity, unit,
                   COALESCE(total_produced, 0) AS total_produced, shift, reason, comments
            FROM public.scrap_logs
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY to_date(date,'MM/DD/YYYY') DESC, id DESC"
        return sql, params

    def _query_df(self, sql: str, params: list) -> pd.DataFrame:
        """Execute SQL with psycopg2 and return a DataFrame (no SQLAlchemy)."""
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
        return pd.DataFrame(rows, columns=cols)

    def fetch_data(self):
        sql, params = self.build_query()
        try:
            self.df = self._query_df(sql, params)
        except Exception as e:
            return messagebox.showerror("DB Error", str(e))

        self.current_page = 1
        self.total_pages = max(1, (len(self.df) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.refresh_pages()
        self.show_page()

    def refresh_pages(self):
        for w in self.pagebar.winfo_children():
            w.destroy()

        def go(p):
            self.current_page = p
            self.show_page()

        tk.Button(self.pagebar, text="<<", command=lambda: go(max(1, self.current_page - 1)),
                  bg="#F8FAFC", relief="flat", font=("Segoe UI", 10)).pack(side="left", padx=3)
        tk.Label(self.pagebar, text=f"Page {self.current_page} of {self.total_pages}",
                 bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(side="left", padx=3)
        tk.Button(self.pagebar, text=">>", command=lambda: go(min(self.total_pages, self.current_page + 1)),
                  bg="#F8FAFC", relief="flat", font=("Segoe UI", 10)).pack(side="left", padx=3)

    def show_page(self):
        self.tree.delete(*self.tree.get_children())
        if self.df.empty:
            return
        start = (self.current_page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        slice_df = self.df.iloc[start:end]
        for i, row in slice_df.iterrows():
            tag = 'even' if i % 2 == 0 else 'odd'
            vals = [row[c] for c in self.visible_cols]
            self.tree.insert("", tk.END, values=vals, tags=(tag,))
        self.tree.tag_configure('even', background="#FFFFFF")
        self.tree.tag_configure('odd', background="#F7F9FB")

    # ---------- Actions ----------
    def export(self):
        if self.df is None or self.df.empty:
            return messagebox.showinfo("Export", "No data to export.")
        fp = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return
        self.df[self.visible_cols].to_csv(fp, index=False)  # export without the hidden id
        messagebox.showinfo("Exported", f"Saved to:\n{fp}")

    def _selected_row_record(self):
        sel = self.tree.selection()
        if not sel:
            return None
        index_in_page = self.tree.index(sel[0])
        df_index = (self.current_page - 1) * PAGE_SIZE + index_in_page
        return self.df.iloc[df_index]

    def delete_selected(self):
        rec = self._selected_row_record()
        if rec is None:
            return messagebox.showinfo("Delete", "Select a row.")
        rec_id = int(rec["id"])

        if not messagebox.askyesno("Confirm", "Delete selected log?"):
            return

        try:
            with get_db_connection() as c, c.cursor() as cur:
                cur.execute("DELETE FROM public.scrap_logs WHERE id=%s", (rec_id,))
                c.commit()
            messagebox.showinfo("Done", "Deleted.")
            self.fetch_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_edit(self):
        rec = self._selected_row_record()
        if rec is None:
            return messagebox.showinfo("Edit", "Select a row.")
        rec_id = int(rec["id"])

        pop = tk.Toplevel(self)
        pop.title("Edit Scrap Log")
        pop.configure(bg="#F8FAFC")
        pop.grab_set()

        fields = {}
        def row(lbl, val, r):
            tk.Label(pop, text=lbl, font=("Segoe UI", 12, "bold"),
                     bg="#F8FAFC", fg="#0F172A").grid(row=r, column=0, sticky="w", padx=6, pady=4)
            e = tk.Entry(pop, font=("Segoe UI", 12), bg="white", fg="#0F172A")
            e.grid(row=r, column=1, padx=6, pady=4, ipady=2, ipadx=3)
            e.insert(0, str(val)); fields[lbl] = e

        row("Machine Operator", rec["machine_operator"], 0)
        row("Machine Name", rec["machine_name"], 1)
        row("Date (MM/DD/YYYY)", rec["date"], 2)
        row("Quantity", rec["quantity"], 3)
        row("Unit", rec["unit"], 4)
        row("Total Produced", rec.get("total_produced", 0), 5)
        row("Shift", rec["shift"], 6)
        row("Reason", rec["reason"], 7)
        row("Comments", rec["comments"], 8)

        def save():
            try:
                m = fields["Machine Operator"].get().strip()
                mn = fields["Machine Name"].get().strip()
                d = fields["Date (MM/DD/YYYY)"].get().strip()
                q = float(fields["Quantity"].get())
                u = fields["Unit"].get().strip()
                tpv = fields["Total Produced"].get().strip()
                tpv = float(tpv) if tpv else None
                s = fields["Shift"].get().strip()
                r = fields["Reason"].get().strip()
                c = fields["Comments"].get().strip()
                datetime.strptime(d, "%m/%d/%Y")
                if q <= 0:
                    raise ValueError("Qty must be > 0")
                with get_db_connection() as conn, conn.cursor() as cur:
                    cur.execute(
                        """UPDATE public.scrap_logs
                           SET machine_operator=%s, machine_name=%s, date=%s, quantity=%s, unit=%s,
                               total_produced=%s, shift=%s, reason=%s, comments=%s
                           WHERE id=%s""",
                        (m, mn, d, q, u, tpv, s, r, c, rec_id)
                    )
                    conn.commit()
                pop.destroy()
                self.fetch_data()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        ttk.Button(pop, text="Save", command=save).grid(row=9, columnspan=2, pady=10)
