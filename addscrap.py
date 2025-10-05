import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from datetime import datetime
from PIL import Image, ImageTk
import sqlite3


class AddScrapFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self.BASE_DIR = os.path.dirname(__file__)
        self.IMAGE_DIR = os.path.join(self.BASE_DIR, "images")
        self.DB_PATH = os.path.join(self.BASE_DIR, "sample_data.db")

        self.scale_x = max(self.winfo_screenwidth() / 1920, 0.8)
        self.scale_y = max(self.winfo_screenheight() / 1080, 0.8)
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.build_form()

    # ---------- UI helpers ----------
    def load_icon(self, name, size):
        path = os.path.join(self.IMAGE_DIR, name)
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def create_entry(self, parent, label, row, placeholder=""):
        tk.Label(parent, text=label, bg="#F8FAFC", fg="#0F172A",
                 font=("Segoe UI", 12, "bold")).grid(row=row, column=0, sticky="e", padx=10, pady=8)
        e = tk.Entry(parent, font=("Segoe UI", 12), bg="white", relief="flat",
                     highlightthickness=1, highlightbackground="#E5E7EB", highlightcolor="#3E84FB")
        e.grid(row=row, column=1, padx=10, pady=8, ipadx=3, ipady=4)
        if placeholder:
            e.insert(0, placeholder)
            e.config(fg="grey")
            e.bind("<FocusIn>", lambda ev: self._clear_placeholder(e, placeholder))
            e.bind("<FocusOut>", lambda ev: self._restore_placeholder(e, placeholder))
        return e

    def _clear_placeholder(self, e, text):
        if e.get() == text:
            e.delete(0, "end")
            e.config(fg="black")

    def _restore_placeholder(self, e, text):
        if not e.get():
            e.insert(0, text)
            e.config(fg="grey")

    # ---------- Build Form ----------
    def build_form(self):
        tk.Label(self, text="Add Scrap Entry",
                 font=("Segoe UI", int(36 * self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#1F3B4D").pack(pady=(30, 20))

        form = tk.Frame(self, bg="#F8FAFC")
        form.pack(pady=10)

        self.operator_entry = self.create_entry(form, "Machine Operator:", 0, "Enter operator name")
        self.machine_entry = self.create_entry(form, "Machine Name:", 1, "Enter machine name")
        self.date_entry = self.create_entry(form, "Date (MM/DD/YYYY):", 2, datetime.today().strftime("%m/%d/%Y"))

        # Calendar picker
        cal_icon = self.load_icon("schedule.png", (20, 20))
        tk.Button(form, image=cal_icon if cal_icon else None, text=("📅" if not cal_icon else ""),
                  command=self.open_calendar, bg="#F8FAFC", bd=0).grid(row=2, column=2, padx=5)
        self.cal_icon = cal_icon

        self.quantity_entry = self.create_entry(form, "Quantity:", 3, "e.g. 100")
        self.unit_entry = self.create_entry(form, "Unit:", 4, "lbs")
        self.total_entry = self.create_entry(form, "Total Produced:", 5, "e.g. 5000")

        tk.Label(form, text="Shift:", bg="#F8FAFC", fg="#0F172A",
                 font=("Segoe UI", 12, "bold")).grid(row=6, column=0, sticky="e", padx=10, pady=8)
        self.shift_combo = ttk.Combobox(form, values=["A", "B", "C"],
                                        font=("Segoe UI", 12), width=10, state="readonly")
        self.shift_combo.set("A")
        self.shift_combo.grid(row=6, column=1, padx=10, pady=8, sticky="w")

        self.reason_entry = self.create_entry(form, "Reason:", 7, "Enter scrap cause")
        self.comment_entry = self.create_entry(form, "Comments:", 8, "Optional comments")

        tk.Button(self, text="Submit Entry", font=("Segoe UI", 14, "bold"),
                  bg="#2563EB", fg="white", relief="flat", cursor="hand2",
                  command=self.save_entry).pack(pady=25, ipadx=20, ipady=5)

    def open_calendar(self):
        top = tk.Toplevel(self)
        top.title("Select Date")
        cal = Calendar(top)
        cal.pack(pady=10)
        ttk.Button(top, text="Select", command=lambda: self._set_date(cal, top)).pack(pady=5)

    def _set_date(self, cal, top):
        date = cal.get_date()
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, date)
        top.destroy()

    # ---------- DB Logic ----------
    def save_entry(self):
        try:
            operator = self.operator_entry.get().strip()
            machine = self.machine_entry.get().strip()
            date = self.date_entry.get().strip()
            quantity = float(self.quantity_entry.get().strip())
            unit = self.unit_entry.get().strip()
            total = float(self.total_entry.get().strip() or 0)
            shift = self.shift_combo.get()
            reason = self.reason_entry.get().strip()
            comments = self.comment_entry.get().strip()

            if not operator or not machine or not date or quantity <= 0:
                raise ValueError("Please fill out all required fields.")

            # Validate date
            datetime.strptime(date, "%m/%d/%Y")

            conn = sqlite3.connect(self.DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scrap_logs
                (machine_operator, machine_name, date, quantity, unit, total_produced, shift, reason, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (operator, machine, date, quantity, unit, total, shift, reason, comments))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Scrap entry added successfully!")
            self._clear_form()

        except ValueError as ve:
            messagebox.showerror("Input Error", str(ve))
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _clear_form(self):
        self.operator_entry.delete(0, "end")
        self.machine_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, datetime.today().strftime("%m/%d/%Y"))
        self.quantity_entry.delete(0, "end")
        self.unit_entry.delete(0, "end")
        self.total_entry.delete(0, "end")
        self.reason_entry.delete(0, "end")
        self.comment_entry.delete(0, "end")
        self.shift_combo.set("A")
