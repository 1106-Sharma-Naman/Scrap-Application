import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import psycopg2
import os

# =========================
# DB CONFIG (env-friendly)
# =========================
# On your Mac (server) you can leave PGHOST=127.0.0.1 while testing.
# On your friend's Windows PC, set PGHOST to your Tailscale IP.
PG_HOST = os.getenv("PGHOST", "127.0.0.1")
PG_DB   = os.getenv("PGDATABASE", "scrapsense")
PG_USER = os.getenv("PGUSER", "scrapsense")
PG_PASS = os.getenv("PGPASSWORD", "scrapsense2006")
PG_PORT = int(os.getenv("PGPORT", "5432"))

ADD_TOTAL_PRODUCED_SQL = """
ALTER TABLE public.scrap_logs
ADD COLUMN IF NOT EXISTS total_produced NUMERIC;
"""

class ViewLogFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self.BASE_DIR = os.path.dirname(__file__)
        self.IMAGE_DIR = os.path.join(self.BASE_DIR, "images")

        # Global caret (insertion cursor) color for all widgets
        self.option_add('*Entry.insertBackground', 'black')
        self.option_add('*Text.insertBackground', 'black')
        self.option_add('*TCombobox*insertBackground', 'black')

        self.scale_x = self.winfo_screenwidth() / 1920
        self.scale_y = self.winfo_screenheight() / 1080
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.shift_suggestions = []

        # Make sure critical column exists (align with Add page)
        self.ensure_total_produced_column()

        self.build_ui()
        self.after(0, self.fetch_data)

    # ---------------- Helpers ----------------
    def enable_focus(self, widget):
        widget.bind("<Button-1>", lambda e: e.widget.focus_set())

    def get_db_connection(self):
        return psycopg2.connect(
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            host=PG_HOST,
            port=str(PG_PORT),
            connect_timeout=5,
            application_name="ScrapSense_ViewLog"
        )

    def ensure_total_produced_column(self):
        try:
            with self.get_db_connection() as conn, conn.cursor() as cur:
                cur.execute(ADD_TOTAL_PRODUCED_SQL)
                conn.commit()
        except Exception as e:
            print("ensure_total_produced_column warning:", e)

    def fetch_shift_suggestions(self):
        try:
            with self.get_db_connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT DISTINCT shift FROM public.scrap_logs WHERE shift IS NOT NULL AND shift <> '' ORDER BY shift ASC")
                rows = cur.fetchall()
            self.shift_suggestions = ["All"] + [r[0] for r in rows if r[0]]
        except Exception:
            self.shift_suggestions = ["All"]

    def load_icon(self, filename, size):
        path = os.path.join(self.IMAGE_DIR, filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        return None

    def add_placeholder(self, entry, placeholder):
        entry.delete(0, tk.END)
        entry.insert(0, placeholder)
        entry.config(fg="grey")

        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(fg="black")

        def on_focus_out(event):
            if entry.get() == "":
                entry.insert(0, placeholder)
                entry.config(fg="grey")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def open_calendar(self, entry_widget):
        top = tk.Toplevel(self)
        top.title("Select Date")
        top.lift()
        cal = Calendar(top, selectmode="day",
                       year=datetime.now().year,
                       month=datetime.now().month,
                       day=datetime.now().day)
        cal.pack(pady=20)

        def pick_date():
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, cal.get_date())
            top.destroy()
            self.fetch_data()

        ttk.Button(top, text="Select", command=pick_date).pack(pady=10)

    def delayed_live_search(self):
        if hasattr(self, "_live_search_after_id"):
            self.after_cancel(self._live_search_after_id)
        self._live_search_after_id = self.after(300, self.fetch_data)

    # ---------------- UI ----------------
    def build_ui(self):
        tk.Label(self, text="Scrap Logs",
                 font=("Segoe UI", int(36 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").pack(pady=int(20 * self.scale_y))

        filter_frame = tk.Frame(self, bg="#F8FAFC")
        filter_frame.pack(pady=int(10 * self.scale_y))

        # Operator filter
        self.operator_entry = tk.Entry(filter_frame,
                                       font=("Segoe UI", int(12 * self.scale_font)),
                                       width=20, bg="white",
                                       relief="groove", borderwidth=1,
                                       highlightthickness=0,
                                       insertbackground="black")
        self.enable_focus(self.operator_entry)
        self.operator_entry.grid(row=0, column=1, padx=int(10 * self.scale_x))
        self.add_placeholder(self.operator_entry, "Search Operator")
        self.operator_entry.bind("<KeyRelease>", lambda e: self.delayed_live_search())

        tk.Label(filter_frame, text="Machine Operator:",
                 font=("Segoe UI", int(12 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=int(10 * self.scale_x))

        # Shift filter
        self.fetch_shift_suggestions()
        self.shift_combo = ttk.Combobox(filter_frame, values=self.shift_suggestions,
                                        font=("Segoe UI", int(12 * self.scale_font)), width=15,
                                        state="normal")
        self.enable_focus(self.shift_combo)
        self.shift_combo.set("All")
        self.shift_combo.grid(row=0, column=3, padx=int(10 * self.scale_x))
        self.shift_combo.bind("<KeyRelease>", lambda e: self.delayed_live_search())
        self.shift_combo.bind("<<ComboboxSelected>>", lambda e: self.fetch_data())

        tk.Label(filter_frame, text="Shift:",
                 font=("Segoe UI", int(12 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=2, padx=int(10 * self.scale_x))

        # Date filters
        self.calendar_icon = self.load_icon("schedule.png",
                                            (int(20 * self.scale_x), int(20 * self.scale_y)))

        self.from_date = tk.Entry(filter_frame,
                                  font=("Segoe UI", int(12 * self.scale_font)), width=15, bg="white",
                                  relief="groove", borderwidth=1,
                                  highlightthickness=0, insertbackground="black")
        self.enable_focus(self.from_date)
        self.from_date.grid(row=0, column=5)
        self.add_placeholder(self.from_date, "MM/DD/YYYY")
        self.from_date.bind("<KeyRelease>", lambda e: self.delayed_live_search())

        tk.Label(filter_frame, text="From Date:",
                 font=("Segoe UI", int(12 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=4, padx=int(10 * self.scale_x))

        tk.Button(filter_frame, image=self.calendar_icon, bg="white", bd=0,
                  command=lambda: self.open_calendar(self.from_date)).grid(row=0, column=6, padx=int(5 * self.scale_x))

        self.to_date = tk.Entry(filter_frame,
                                font=("Segoe UI", int(12 * self.scale_font)), width=15, bg="white",
                                relief="groove", borderwidth=1,
                                highlightthickness=0, insertbackground="black")
        self.enable_focus(self.to_date)
        self.to_date.grid(row=0, column=8)
        self.add_placeholder(self.to_date, "MM/DD/YYYY")
        self.to_date.bind("<KeyRelease>", lambda e: self.delayed_live_search())

        tk.Label(filter_frame, text="To Date:",
                 font=("Segoe UI", int(12 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=7, padx=int(10 * self.scale_x))

        tk.Button(filter_frame, image=self.calendar_icon, bg="white", bd=0,
                  command=lambda: self.open_calendar(self.to_date)).grid(row=0, column=9, padx=int(5 * self.scale_x))

        # Table
        table_frame = tk.Frame(self, bg="#F8FAFC")
        table_frame.pack(fill="both", expand=True,
                         padx=int(20 * self.scale_x), pady=int(20 * self.scale_y))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white",
                        rowheight=int(35 * self.scale_y),
                        font=("Segoe UI", int(12 * self.scale_font)),
                        borderwidth=1, relief="flat")
        style.configure("Treeview.Heading", background="#F1F5F9", foreground="black",
                        font=("Segoe UI", int(12 * self.scale_font), "bold"))
        style.map("Treeview", background=[("selected", "#3E84FB")], foreground=[("selected", "white")])

        # NOTE: include total_produced so it matches Add page & DB
        columns = ("id", "machine_operator", "date", "quantity", "unit", "total_produced", "shift", "reason", "comments")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, style="Treeview")
        pretty = {
            "id": "ID",
            "machine_operator": "Machine Operator",
            "date": "Date",
            "quantity": "Quantity",
            "unit": "Unit",
            "total_produced": "Total Produced",
            "shift": "Shift",
            "reason": "Reason",
            "comments": "Comments",
        }
        for col in columns:
            self.tree.heading(col, text=pretty[col])
            # wider columns for comments & reason
            width = 220 if col in ("comments", "reason") else 150
            self.tree.column(col, width=int(width * self.scale_x), anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_frame = tk.Frame(self, bg="#F8FAFC")
        btn_frame.pack(pady=int(10 * self.scale_y))
        ttk.Button(btn_frame, text="Refresh", command=self.reset_filters).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected_entry).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.open_edit_window).grid(row=0, column=2, padx=5)

    # ---------------- Data ----------------
    def fetch_data(self):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()

            # Build WHERE with optional filters. Use to_date() so text dates compare correctly.
            where = ["1=1"]
            params = []

            op_val = self.operator_entry.get().strip()
            if op_val and op_val != "Search Operator":
                where.append("machine_operator ILIKE %s")
                params.append(f"%{op_val}%")

            shift_val = self.shift_combo.get().strip()
            if shift_val and shift_val != "All":
                where.append("shift ILIKE %s")
                params.append(f"%{shift_val}%")

            from_val = self.from_date.get().strip()
            if from_val and from_val != "MM/DD/YYYY":
                where.append("to_date(date, 'MM/DD/YYYY') >= to_date(%s, 'MM/DD/YYYY')")
                params.append(from_val)

            to_val = self.to_date.get().strip()
            if to_val and to_val != "MM/DD/YYYY":
                where.append("to_date(date, 'MM/DD/YYYY') <= to_date(%s, 'MM/DD/YYYY')")
                params.append(to_val)

            query = f"""
                SELECT id, machine_operator, date, quantity, unit, COALESCE(total_produced, 0), shift, reason, comments
                FROM public.scrap_logs
                WHERE {' AND '.join(where)}
                ORDER BY to_date(date, 'MM/DD/YYYY') DESC, id DESC
            """

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            conn.close()

            self.tree.delete(*self.tree.get_children())
            for i, row in enumerate(rows):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.tree.insert("", tk.END, values=row, tags=(tag,))
            self.tree.tag_configure('evenrow', background="#F8FAFC")
            self.tree.tag_configure('oddrow', background="#E2E8F0")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data:\n{e}")

    def reset_filters(self):
        self.operator_entry.delete(0, tk.END)
        self.add_placeholder(self.operator_entry, "Search Operator")
        self.fetch_shift_suggestions()
        self.shift_combo["values"] = self.shift_suggestions
        self.shift_combo.set("All")
        self.from_date.delete(0, tk.END)
        self.add_placeholder(self.from_date, "MM/DD/YYYY")
        self.to_date.delete(0, tk.END)
        self.add_placeholder(self.to_date, "MM/DD/YYYY")
        self.fetch_data()

    def delete_selected_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a record to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected log?"):
            record_id = self.tree.item(selected[0])["values"][0]
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM public.scrap_logs WHERE id = %s", (record_id,))
                conn.commit()
                conn.close()
                self.fetch_data()
                messagebox.showinfo("Deleted", "Scrap log deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    def open_edit_window(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record to edit.")
            return
        values = self.tree.item(selected[0])["values"]
        record_id = values[0]

        edit_win = tk.Toplevel(self)
        edit_win.title("Edit Scrap Log")
        edit_win.configure(bg="#F8FAFC")
        edit_win.grab_set()
        edit_win.resizable(False, False)

        entry_fields = {}
        self.fetch_shift_suggestions()

        labels = [
            ("Machine Operator (ID):", "machine_operator", values[1]),
            ("Date (MM/DD/YYYY):", "date", values[2]),
            ("Quantity:", "quantity", values[3]),
            ("Unit:", "unit", values[4]),
            ("Total Produced:", "total_produced", values[5]),
            ("Shift:", "shift", values[6]),
            ("Reason:", "reason", values[7]),
            ("Comments:", "comments", values[8]),
        ]

        for i, (lbl, key, val) in enumerate(labels):
            tk.Label(edit_win, text=lbl, font=("Segoe UI", 12, "bold"),
                     anchor="w", bg="#F8FAFC", fg="#334155").grid(row=i, column=0, sticky="w", padx=12, pady=7)
            if key == "comments":
                entry = tk.Text(edit_win, height=4, width=40, font=("Segoe UI", 12),
                                fg="black", bg="white", insertbackground="black")
                self.enable_focus(entry)
                entry.insert("1.0", val)
            elif key == "unit":
                entry = ttk.Combobox(edit_win, values=["lb", "kg", "units", "grams"],
                                     font=("Segoe UI", 12), width=12, state="normal")
                self.enable_focus(entry)
                entry.set(val)
            elif key == "shift":
                entry = ttk.Combobox(edit_win, values=self.shift_suggestions[1:],
                                     font=("Segoe UI", 12), width=16, state="normal")
                self.enable_focus(entry)
                entry.set(val)
            else:
                entry = tk.Entry(edit_win, font=("Segoe UI", 12), width=40,
                                 fg="black", bg="white", insertbackground="black")
                self.enable_focus(entry)
                entry.insert(0, val)
            entry.grid(row=i, column=1, padx=8, pady=7, sticky="w")
            entry_fields[key] = entry

        def save_changes():
            try:
                mop = entry_fields["machine_operator"].get().strip()
                date = entry_fields["date"].get().strip()
                qty = entry_fields["quantity"].get().strip()
                unit = entry_fields["unit"].get().strip()
                tot_prod = entry_fields["total_produced"].get().strip()
                shift = entry_fields["shift"].get().strip().upper()
                reason = entry_fields["reason"].get().strip()
                comments = entry_fields["comments"].get("1.0", tk.END).strip()

                if not mop or not date or not qty or not unit or not shift:
                    messagebox.showerror("Validation Error", "Required fields are missing.")
                    return

                # Basic validation
                datetime.strptime(date, "%m/%d/%Y")
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError("Quantity must be positive")
                tot_val = float(tot_prod) if tot_prod else None
                if tot_val is not None and tot_val <= 0:
                    raise ValueError("Total Produced must be positive")

                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE public.scrap_logs
                    SET machine_operator=%s, date=%s, quantity=%s, unit=%s,
                        total_produced=%s, shift=%s, reason=%s, comments=%s
                    WHERE id=%s
                """, (mop, date, qty_val, unit, tot_val, shift, reason, comments, record_id))
                conn.commit()
                conn.close()

                messagebox.showinfo("Updated", "Log updated successfully.")
                edit_win.destroy()
                self.fetch_data()

            except ValueError as ve:
                messagebox.showerror("Validation Error", str(ve))
            except Exception as e:
                messagebox.showerror("Error", f"Could not update entry:\n{e}")

        ttk.Button(edit_win, text="Save", command=save_changes).grid(row=len(labels), column=0, columnspan=2, pady=16)
