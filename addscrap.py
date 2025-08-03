import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import pandas as pd
import sqlite3
import os

# --- Database Setup ---
DB_FILE = "scrap_logs.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_operator TEXT NOT NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            shift TEXT NOT NULL,
            reason TEXT,
            comments TEXT,
            UNIQUE(machine_operator, date) -- Prevent duplicates for same operator/date
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Window Setup ---
root = tk.Tk()
root.title("ScrapSense - Add Scrap")
root.geometry("1920x1080")
root.configure(bg="#F8FAFC")  # Softer background

# --- Global dictionary for fields ---
fields = {}

# --- Function to Update Time ---
def update_time():
    now = datetime.now()
    time_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
    root.after(1000, update_time)

# --- Function to Load Icons ---
def load_icon(path, size):
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except FileNotFoundError:
        return None

# --- Sidebar ---
sidebar = tk.Frame(root, bg="#1E293B", width=80)
sidebar.pack(side="left", fill="y")

# Logo
logo_img = load_icon("scraplogo.png", (50, 50))
if logo_img:
    tk.Label(sidebar, image=logo_img, bg="#1E293B").pack(pady=30)

# Navigation Icons
nav_icons = [
    ("dashboard.png", "Dashboard"),
    ("add-button.png", "Add Scrap"),
    ("prediction.png", "Predictions"),
    ("doc.png", "Scrap Logs"),
    ("report-card.png", "Reports"),
    ("setting.png", "Settings")
]

def on_hover(e, color):
    e.widget.config(bg=color)

for icon_path, tooltip in nav_icons:
    icon_img = load_icon(icon_path, (30, 30))
    if icon_img:
        btn = tk.Label(sidebar, image=icon_img, bg="#1E293B", width=80, height=60)
        btn.image = icon_img
        btn.pack(pady=8)
        btn.bind("<Enter>", lambda e, c="#334155": on_hover(e, c))
        btn.bind("<Leave>", lambda e, c="#1E293B": on_hover(e, c))

# --- Main Frame ---
main_frame = tk.Frame(root, bg="#F8FAFC")
main_frame.pack(side="left", fill="both", expand=True)

# Welcome & Time
username = "Akshay"
tk.Label(main_frame, text=f"Welcome, {username}", font=("Segoe UI", 24, "bold"),
         bg="#F8FAFC", fg="#1E293B").place(x=100, y=50)

time_label = tk.Label(main_frame, font=("Segoe UI", 14), bg="#F8FAFC", fg="#475569")
time_label.place(relx=0.98, y=40, anchor="ne")
update_time()

# Title
tk.Label(main_frame, text="Add Scrap", font=("Segoe UI", 46, "bold"),
         bg="#F8FAFC", fg="#0F172A").pack(pady=(80, 40))

# --- Form Frame ---
form_frame = tk.Frame(main_frame, bg="white", padx=40, pady=40,
                      highlightbackground="#E2E8F0", highlightthickness=1)
form_frame.pack(pady=20)

# Combobox Styling
style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black", padding=5)

# --- Field Creator ---
def create_field(label_text, key, row, is_textbox=False, is_dropdown=False, default=""):
    tk.Label(form_frame, text=label_text, font=("Segoe UI", 14, "bold"),
             bg="white", fg="#334155", anchor="w").grid(row=row, column=0, sticky="w", pady=12, padx=10)

    if is_textbox:
        entry = tk.Text(form_frame, width=50, height=5, font=("Segoe UI", 12),
                        fg="black", bg="#F9FAFB", relief="flat",
                        highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
        entry.grid(row=row, column=1, pady=12, ipady=5)
    elif is_dropdown:
        entry = ttk.Combobox(form_frame, values=["Morning", "Afternoon", "Night"], width=47, font=("Segoe UI", 12))
        entry.set(default or "Select Shift")
        entry.grid(row=row, column=1, pady=12)
    else:
        entry = tk.Entry(form_frame, width=50, font=("Segoe UI", 12),
                         fg="black", bg="#F9FAFB", relief="flat",
                         highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
        entry.insert(0, default)
        entry.grid(row=row, column=1, pady=12, ipady=5)

    fields[key] = entry
    return entry

# --- Fields ---
create_field("Machine Operator (ID):", "machine_operator", 0)

# Date Picker
tk.Label(form_frame, text="Date (MM/DD/YYYY):", font=("Segoe UI", 14, "bold"),
         bg="white", fg="#334155", anchor="w").grid(row=1, column=0, sticky="w", pady=12, padx=10)

date_frame = tk.Frame(form_frame, bg="white")
date_frame.grid(row=1, column=1, pady=12, sticky="w")

fields["date"] = tk.Entry(date_frame, width=47, font=("Segoe UI", 12),
                          fg="black", bg="#F9FAFB", relief="flat",
                          highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
fields["date"].insert(0, datetime.now().strftime("%m/%d/%Y"))
fields["date"].pack(side="left", ipady=5)

def open_calendar():
    top = tk.Toplevel(root)
    top.title("Select Date")
    cal = Calendar(top, selectmode="day", year=datetime.now().year,
                   month=datetime.now().month, day=datetime.now().day)
    cal.pack(pady=20)

    def pick_date():
        fields["date"].delete(0, tk.END)
        fields["date"].insert(0, cal.get_date())
        top.destroy()

    ttk.Button(top, text="Select", command=pick_date).pack(pady=10)

calendar_icon = load_icon("schedule.png", (20, 20))
if calendar_icon:
    tk.Button(date_frame, image=calendar_icon, command=open_calendar, bg="white", bd=0, cursor="hand2").pack(side="left", padx=5)

# Other fields
create_field("Quantity:", "quantity", 2)
create_field("Shift:", "shift", 3, is_dropdown=True)
create_field("Reason:", "reason", 4)
create_field("Additional Comments:", "comments", 5, is_textbox=True)

# --- SCADA Import ---
def import_scada_report():
    try:
        file_path = filedialog.askopenfilename(
            title="Select SCADA Report",
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*")
            ]
        )

        if not file_path:
            return  # Cancelled

        # Load CSV or Excel
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)

        if df.empty:
            messagebox.showwarning("Empty File", "The selected file has no data.")
            return

        df.columns = df.columns.str.strip().str.lower()
        row = df.iloc[0].to_dict()

        def get_value(*possible_names, default=""):
            for name in possible_names:
                if name.lower() in row and pd.notna(row[name.lower()]):
                    return str(row[name.lower()])
            return default

        fields["machine_operator"].delete(0, tk.END)
        fields["machine_operator"].insert(0, get_value("machine operator id", "operator id", "operator"))

        fields["date"].delete(0, tk.END)
        fields["date"].insert(0, get_value("date", default=datetime.now().strftime("%m/%d/%Y")))

        fields["quantity"].delete(0, tk.END)
        fields["quantity"].insert(0, get_value("quantity", "scrap quantity"))

        fields["shift"].set(get_value("shift", default="Select Shift"))

        fields["reason"].delete(0, tk.END)
        fields["reason"].insert(0, get_value("reason", "scrap reason"))

        fields["comments"].delete("1.0", tk.END)
        fields["comments"].insert("1.0", get_value("comments", "notes"))

        messagebox.showinfo("Success", "SCADA report imported successfully!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to import file:\n{e}")

# --- Submit Scrap Entry ---
def submit_scrap_entry():
    machine_operator = fields["machine_operator"].get().strip()
    date = fields["date"].get().strip()
    quantity = fields["quantity"].get().strip()
    shift = fields["shift"].get().strip()
    reason = fields["reason"].get().strip()
    comments = fields["comments"].get("1.0", tk.END).strip()

    # Validation
    if not machine_operator or not date or not quantity or shift == "Select Shift":
        messagebox.showerror("Validation Error", "Please fill in all required fields.")
        return

    try:
        quantity = float(quantity)
    except ValueError:
        messagebox.showerror("Validation Error", "Quantity must be a number.")
        return

    # Save to DB
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrap_logs (machine_operator, date, quantity, shift, reason, comments)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (machine_operator, date, quantity, shift, reason, comments))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Scrap entry saved successfully!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Duplicate Entry", "An entry for this operator and date already exists.")
    except Exception as e:
        messagebox.showerror("Database Error", f"An error occurred: {e}")

# --- Buttons ---
style.configure("Blue.TButton", background="#3B82F6", foreground="white", font=("Segoe UI", 14, "bold"), padding=10)
style.map("Blue.TButton", background=[("active", "#2563EB")])

style.configure("Green.TButton", background="#22C55E", foreground="white", font=("Segoe UI", 16, "bold"), padding=10)
style.map("Green.TButton", background=[("active", "#16A34A")])

ttk.Button(main_frame, text="Import SCADA Report", style="Blue.TButton", cursor="hand2", command=import_scada_report).pack(pady=(10, 5), ipady=5)
ttk.Button(main_frame, text="Submit Scrap Entry", style="Green.TButton", cursor="hand2", command=submit_scrap_entry).pack(pady=30, ipady=5)

root.mainloop()
