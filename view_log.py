import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import psycopg2
import os


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
        self.build_ui()
        self.after(0, self.fetch_data)

    def enable_focus(self, widget):
        """Force widget to grab focus on click."""
        widget.bind("<Button-1>", lambda e: e.widget.focus_set())

    def get_db_connection(self):
        return psycopg2.connect(
            dbname="scrapsense",
            user="postgres",
            password="",
            host="localhost",
            port="5432"
        )

    def fetch_shift_suggestions(self):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT shift FROM scrap_logs ORDER BY shift ASC")
            rows = cur.fetchall()
            cur.close()
            conn.close()
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

        columns = ("id", "machine_operator", "date", "quantity", "unit", "shift", "reason", "comments")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, style="Treeview")
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=int(150 * self.scale_x), anchor="center")
        self.tree.pack(fill="both", expand=True)

        btn_frame = tk.Frame(self, bg="#F8FAFC")
        btn_frame.pack(pady=int(10 * self.scale_y))
        ttk.Button(btn_frame, text="Refresh", command=self.reset_filters).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected_entry).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.open_edit_window).grid(row=0, column=2, padx=5)

    def fetch_data(self):
        conn = self.get_db_connection()
        c = conn.cursor()
        query = "SELECT * FROM scrap_logs WHERE 1=1"
        params = []
        if self.operator_entry.get().strip() and self.operator_entry.get() != "Search Operator":
            query += " AND machine_operator ILIKE %s"
            params.append(f"%{self.operator_entry.get().strip()}%")
        if self.shift_combo.get() != "All" and self.shift_combo.get().strip():
            query += " AND shift ILIKE %s"
            params.append(f"%{self.shift_combo.get().strip()}%")
        if self.from_date.get().strip() and self.from_date.get() != "MM/DD/YYYY":
            query += " AND date >= %s"
            params.append(self.from_date.get().strip())
        if self.to_date.get().strip() and self.to_date.get() != "MM/DD/YYYY":
            query += " AND date <= %s"
            params.append(self.to_date.get().strip())
        c.execute(query, tuple(params))
        rows = c.fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", tk.END, values=row, tags=(tag,))
        self.tree.tag_configure('evenrow', background="#F8FAFC")
        self.tree.tag_configure('oddrow', background="#E2E8F0")

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
                c = conn.cursor()
                c.execute("DELETE FROM scrap_logs WHERE id = %s", (record_id,))
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
            ("Shift:", "shift", values[5]),
            ("Reason:", "reason", values[6]),
            ("Comments:", "comments", values[7]),
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
            mop = entry_fields["machine_operator"].get().strip()
            date = entry_fields["date"].get().strip()
            qty = entry_fields["quantity"].get().strip()
            unit = entry_fields["unit"].get().strip()
            shift = entry_fields["shift"].get().strip().upper()
            reason = entry_fields["reason"].get().strip()
            comments = entry_fields["comments"].get("1.0", tk.END).strip()
            if not mop or not date or not qty or not unit or not shift:
                messagebox.showerror("Validation Error", "Required fields are missing.")
                return
            try:
                datetime.strptime(date, "%m/%d/%Y")
                qty_val = float(qty)
                if qty_val <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Validation Error", "Invalid quantity or date.")
                return
            try:
                conn = self.get_db_connection()
                c = conn.cursor()
                c.execute("""
                    UPDATE scrap_logs
                    SET machine_operator=%s, date=%s, quantity=%s, unit=%s, shift=%s, reason=%s, comments=%s
                    WHERE id=%s
                """, (mop, date, qty_val, unit, shift, reason, comments, record_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Updated", "Log updated successfully.")
                edit_win.destroy()
                self.fetch_data()
            except Exception as e:
                messagebox.showerror("Error", f"Could not update entry:\n{e}")

        ttk.Button(edit_win, text="Save", command=save_changes).grid(row=len(labels), column=0, columnspan=2, pady=16)
