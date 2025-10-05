import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from PIL import Image, ImageTk
import sqlite3
import pandas as pd
from datetime import datetime

PAGE_SIZE = 50


class ViewLogFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self.BASE_DIR = os.path.dirname(__file__)
        self.IMAGE_DIR = os.path.join(self.BASE_DIR, "images")
        self.DB_PATH = os.path.join(self.BASE_DIR, "sample_data.db")

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
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def add_placeholder(self, e, t):
        e.insert(0, t)
        e.config(fg="grey")

        def _in(_):
            if e.get() == t:
                e.delete(0, "end")
                e.config(fg="black")

        def _out(_):
            if not e.get():
                e.insert(0, t)
                e.config(fg="grey")

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

        filt = tk.Frame(self, bg="#F8FAFC")
        filt.pack(pady=int(5 * self.scale_y))

        tk.Label(filt, text="Machine Operator:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=4, sticky="e")
        self.op_entry = tk.Entry(filt, font=("Segoe UI", 12), width=18, bg="white", relief="flat")
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
        self.from_date = tk.Entry(filt, font=("Segoe UI", 12), width=12, bg="white", relief="flat")
        self.from_date.grid(row=0, column=5, padx=4)
        self.add_placeholder(self.from_date, "MM/DD/YYYY")

        tk.Label(filt, text="To:", font=("Segoe UI", 12, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=6, padx=12, sticky="e")
        self.to_date = tk.Entry(filt, font=("Segoe UI", 12), width=12, bg="white", relief="flat")
        self.to_date.grid(row=0, column=7, padx=4)
        self.add_placeholder(self.to_date, "MM/DD/YYYY")

        reset_btn = self.colored_btn(filt, "Reset", "#2563EB", self.reset_filters, "#1554C9", width=8, height=1)
        reset_btn.grid(row=0, column=8, padx=(12, 4))

        table_frame = tk.Frame(self, bg="#F8FAFC")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

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

        action_bar = tk.Frame(self, bg="#F8FAFC")
        action_bar.pack(pady=10)
        btns = tk.Frame(action_bar, bg="#F8FAFC")
        btns.pack()
        self.colored_btn(btns, "Export CSV", "#2563EB", self.export, "#1554C9").pack(side="left", padx=8)
        self.colored_btn(btns, "Delete", "#EF4444", self.delete_selected, "#C92C2C").pack(side="left", padx=8)

        pag = tk.Frame(self, bg="#F8FAFC")
        pag.pack(pady=(0, 10))
        self.pagebar = pag

    # ---------- Filters / pagination ----------
    def reset_filters(self):
        self.op_entry.delete(0, tk.END)
        self.add_placeholder(self.op_entry, "Search Operator")
        self.shift_combo.set("All")
        self.from_date.delete(0, tk.END)
        self.add_placeholder(self.from_date, "MM/DD/YYYY")
        self.to_date.delete(0, tk.END)
        self.add_placeholder(self.to_date, "MM/DD/YYYY")
        self.fetch_data()

    def _delayed(self):
        if hasattr(self, "_after_id"):
            self.after_cancel(self._after_id)
        self._after_id = self.after(300, self.fetch_data)

    # ---------- SQLite Query ----------
    def fetch_data(self):
        try:
            conn = sqlite3.connect(self.DB_PATH)
            query = "SELECT * FROM scrap_logs WHERE 1=1"
            params = []

            op = self.op_entry.get().strip()
            if op and op != "Search Operator":
                query += " AND machine_operator LIKE ?"
                params.append(f"%{op}%")

            shift = self.shift_combo.get()
            if shift != "All":
                query += " AND shift = ?"
                params.append(shift)

            fd = self.from_date.get().strip()
            td = self.to_date.get().strip()
            if fd and fd != "MM/DD/YYYY":
                query += " AND date >= ?"
                params.append(fd)
            if td and td != "MM/DD/YYYY":
                query += " AND date <= ?"
                params.append(td)

            query += " ORDER BY date DESC"
            self.df = pd.read_sql_query(query, conn, params=params)
            conn.close()

            self.current_page = 1
            self.total_pages = max(1, (len(self.df) + PAGE_SIZE - 1) // PAGE_SIZE)
            self.refresh_pages()
            self.show_page()

        except Exception as e:
            messagebox.showerror("Database Error", str(e))

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
            vals = [row.get(c, "") for c in self.visible_cols]
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", tk.END, values=vals, tags=(tag,))
        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F7F9FB")

    # ---------- Actions ----------
    def export(self):
        if self.df is None or self.df.empty:
            return messagebox.showinfo("Export", "No data to export.")
        fp = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV Files", "*.csv")])
        if not fp:
            return
        self.df[self.visible_cols].to_csv(fp, index=False)
        messagebox.showinfo("Exported", f"Saved to:\n{fp}")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Delete", "Select a row first.")
        item = self.tree.item(sel[0])["values"]
        date, operator = item[2], item[0]
        confirm = messagebox.askyesno("Confirm", f"Delete entry for {operator} on {date}?")
        if not confirm:
            return
        try:
            conn = sqlite3.connect(self.DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM scrap_logs WHERE machine_operator=? AND date=?", (operator, date))
            conn.commit()
            conn.close()
            self.fetch_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
