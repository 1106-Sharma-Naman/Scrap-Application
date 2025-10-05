import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# --- Database helper ---
def get_connection():
    """Returns SQLite connection to local sample_data.db"""
    db_path = os.path.join(os.path.dirname(__file__), "sample_data.db")
    return sqlite3.connect(db_path)


class GenerateReportFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller

        self.scale_x = max(self.winfo_screenwidth() / 1920, 0.8)
        self.scale_y = max(self.winfo_screenheight() / 1080, 0.8)
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.df = pd.DataFrame()
        self.build_ui()

    # ---- UI setup ----
    def build_ui(self):
        tk.Label(self, text="Generate Report",
                 font=("Segoe UI", int(36 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").pack(pady=int(30 * self.scale_y))

        filter_frame = tk.Frame(self, bg="#F8FAFC")
        filter_frame.pack(pady=10)

        tk.Label(filter_frame, text="From Date (MM/DD/YYYY):",
                 font=("Segoe UI", 12, "bold"), bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=6)
        self.from_entry = tk.Entry(filter_frame, font=("Segoe UI", 12), width=15)
        self.from_entry.grid(row=0, column=1, padx=6)

        tk.Label(filter_frame, text="To Date (MM/DD/YYYY):",
                 font=("Segoe UI", 12, "bold"), bg="#F8FAFC", fg="#0F172A").grid(row=0, column=2, padx=6)
        self.to_entry = tk.Entry(filter_frame, font=("Segoe UI", 12), width=15)
        self.to_entry.grid(row=0, column=3, padx=6)

        ttk.Button(filter_frame, text="Generate", command=self.generate_report).grid(row=0, column=4, padx=8)
        ttk.Button(filter_frame, text="Export CSV", command=self.export_csv).grid(row=0, column=5, padx=8)

        self.table_frame = tk.Frame(self, bg="#F8FAFC")
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(self.table_frame, columns=("Date", "Operator", "Machine", "Quantity", "Shift", "Reason"),
                                 show="headings", height=15)
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=int(160 * self.scale_x))
        self.tree.pack(fill="both", expand=True)

        self.chart_frame = tk.Frame(self, bg="#F8FAFC")
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # ---- Generate Report ----
    def generate_report(self):
        start_date = self.from_entry.get().strip()
        end_date = self.to_entry.get().strip()

        try:
            conn = get_connection()
            query = "SELECT date, machine_operator, machine_name, quantity, shift, reason FROM scrap_logs"
            params = []
            if start_date and end_date:
                query += " WHERE date BETWEEN ? AND ?"
                params = [start_date, end_date]

            df = pd.read_sql_query(query, conn, params=params)
            conn.close()

            if df.empty:
                messagebox.showinfo("No Data", "No records found for the selected date range.")
                return

            self.df = df
            self.update_table(df)
            self.generate_chart(df)

        except Exception as e:
            messagebox.showerror("Error", f"Could not generate report:\n{e}")

    # ---- Update table ----
    def update_table(self, df):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(row["date"], row["machine_operator"],
                                                row["machine_name"], row["quantity"],
                                                row["shift"], row["reason"]))

    # ---- Chart ----
    def generate_chart(self, df):
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Aggregate by reason
        reason_data = df.groupby("reason")["quantity"].sum().sort_values(ascending=False)

        fig, ax = plt.subplots(figsize=(6, 4))
        reason_data.plot(kind="bar", color="#2563EB", ax=ax)
        ax.set_title("Scrap Quantity by Reason")
        ax.set_xlabel("Reason")
        ax.set_ylabel("Total Scrap Quantity")
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---- Export ----
    def export_csv(self):
        if self.df.empty:
            return messagebox.showinfo("Export", "No data to export.")
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        self.df.to_csv(file_path, index=False)
        messagebox.showinfo("Exported", f"Report saved to:\n{file_path}")
