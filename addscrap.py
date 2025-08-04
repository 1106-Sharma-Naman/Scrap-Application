import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import pandas as pd
import sqlite3
import os

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)        # directory where script is
IMAGE_DIR = os.path.join(BASE_DIR, "images") # images folder in repo

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
            UNIQUE(machine_operator, date)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Window Setup ---
root = tk.Tk()
root.title("ScrapSense - Add Scrap")
root.configure(bg="#F8FAFC")

# Get screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Scaling factors (base: 1920x1080)
scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

fields = {}

# --- Function to Update Time ---
def update_time():
    now = datetime.now()
    time_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
    root.after(1000, update_time)

# --- Function to Load Icons ---
def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except FileNotFoundError:
        return None

# --- Sidebar ---
sidebar_width = int(80 * scale_x)
sidebar = tk.Frame(root, bg="#1E293B", width=sidebar_width)
sidebar.pack(side="left", fill="y")

logo_img = load_icon("scraplogo.png", (int(50 * scale_x), int(50 * scale_y)))
if logo_img:
    tk.Label(sidebar, image=logo_img, bg="#1E293B").pack(pady=int(30 * scale_y))

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
    icon_img = load_icon(icon_path, (int(30 * scale_x), int(30 * scale_y)))
    if icon_img:
        btn = tk.Label(sidebar, image=icon_img, bg="#1E293B",
                       width=sidebar_width, height=int(60 * scale_y))
        btn.image = icon_img
        btn.pack(pady=int(8 * scale_y))
        btn.bind("<Enter>", lambda e, c="#334155": on_hover(e, c))
        btn.bind("<Leave>", lambda e, c="#1E293B": on_hover(e, c))

# --- Main Frame ---
main_frame = tk.Frame(root, bg="#F8FAFC")
main_frame.pack(side="left", fill="both", expand=True)

username = "Akshay"
tk.Label(main_frame, text=f"Welcome, {username}",
         font=("Segoe UI", int(24 * scale_font), "bold"),
         bg="#F8FAFC", fg="#1E293B").place(x=int(100 * scale_x), y=int(50 * scale_y))

time_label = tk.Label(main_frame, font=("Segoe UI", int(14 * scale_font)),
                      bg="#F8FAFC", fg="#475569")
time_label.place(relx=0.98, y=int(40 * scale_y), anchor="ne")
update_time()

tk.Label(main_frame, text="Add Scrap",
         font=("Segoe UI", int(46 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").pack(pady=(int(80 * scale_y), int(40 * scale_y)))

# --- Form Frame ---
form_frame = tk.Frame(main_frame, bg="white",
                      padx=int(40 * scale_x), pady=int(40 * scale_y),
                      highlightbackground="#E2E8F0", highlightthickness=1)
form_frame.pack(pady=int(20 * scale_y))

style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black", padding=int(5 * scale_y))

# --- First Option Selector ---
tk.Label(form_frame, text="Entry Type:", font=("Segoe UI", int(14 * scale_font), "bold"),
         bg="white", fg="#334155").grid(row=0, column=0, sticky="w",
                                        pady=int(12 * scale_y), padx=int(10 * scale_x))

entry_type = ttk.Combobox(form_frame, values=["Manual Entry", "SCADA Import"],
                          width=int(47 * scale_x), font=("Segoe UI", int(12 * scale_font)))
entry_type.set("Select Entry Type")
entry_type.grid(row=0, column=1, pady=int(12 * scale_y))
fields["entry_type"] = entry_type

def handle_entry_type_change(event):
    if entry_type.get() == "SCADA Import":
        import_scada_report()

entry_type.bind("<<ComboboxSelected>>", handle_entry_type_change)

# --- Field Creator ---
def create_field(label_text, key, row, is_textbox=False, is_dropdown=False, default="", inline_widget=None):
    tk.Label(form_frame, text=label_text, font=("Segoe UI", int(14 * scale_font), "bold"),
             bg="white", fg="#334155", anchor="w").grid(row=row, column=0, sticky="w",
                                                        pady=int(12 * scale_y), padx=int(10 * scale_x))

    if inline_widget:
        inline_widget.grid(row=row, column=1, pady=int(12 * scale_y), sticky="w")
        return inline_widget
    elif is_textbox:
        entry = tk.Text(form_frame, width=int(50 * scale_x), height=5,
                        font=("Segoe UI", int(12 * scale_font)),
                        fg="black", bg="#F9FAFB", relief="flat",
                        highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
        entry.grid(row=row, column=1, pady=int(12 * scale_y), ipady=int(5 * scale_y))
        fields[key] = entry
        return entry
    elif is_dropdown:
        entry = ttk.Combobox(form_frame, values=["Morning", "Afternoon", "Night"],
                             width=int(47 * scale_x), font=("Segoe UI", int(12 * scale_font)))
        entry.set(default or "Select Shift")
        entry.grid(row=row, column=1, pady=int(12 * scale_y))
        fields[key] = entry
        return entry
    else:
        entry = tk.Entry(form_frame, width=int(50 * scale_x), font=("Segoe UI", int(12 * scale_font)),
                         fg="black", bg="#F9FAFB", relief="flat",
                         highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
        entry.insert(0, default)
        entry.grid(row=row, column=1, pady=int(12 * scale_y), ipady=int(5 * scale_y))
        fields[key] = entry
        return entry

# --- Fields ---
create_field("Machine Operator (ID):", "machine_operator", 1)

# Date Field
tk.Label(form_frame, text="Date (MM/DD/YYYY):", font=("Segoe UI", int(14 * scale_font), "bold"),
         bg="white", fg="#334155", anchor="w").grid(row=2, column=0, sticky="w",
                                                    pady=int(12 * scale_y), padx=int(10 * scale_x))

date_frame = tk.Frame(form_frame, bg="white")
date_frame.grid(row=2, column=1, pady=int(12 * scale_y), sticky="w")

fields["date"] = tk.Entry(date_frame, width=int(47 * scale_x),
                          font=("Segoe UI", int(12 * scale_font)),
                          fg="black", bg="#F9FAFB", relief="flat",
                          highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
fields["date"].insert(0, datetime.now().strftime("%m/%d/%Y"))
fields["date"].pack(side="left", ipady=int(5 * scale_y))

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

calendar_icon = load_icon("schedule.png", (int(20 * scale_x), int(20 * scale_y)))
if calendar_icon:
    tk.Button(date_frame, image=calendar_icon, command=open_calendar,
              bg="white", bd=0, cursor="hand2").pack(side="left", padx=int(5 * scale_x))

# Quantity & Unit
quantity_frame = tk.Frame(form_frame, bg="white")
quantity_entry = tk.Entry(quantity_frame, width=int(30 * scale_x),
                          font=("Segoe UI", int(12 * scale_font)),
                          fg="black", bg="#F9FAFB", relief="flat",
                          highlightthickness=2, highlightbackground="#E2E8F0", highlightcolor="#2563EB")
quantity_entry.pack(side="left", ipady=int(5 * scale_y))

unit_dropdown = ttk.Combobox(quantity_frame, values=["lb", "kg", "units", "grams"],
                             width=5, font=("Segoe UI", int(12 * scale_font)))
unit_dropdown.set("Select")
unit_dropdown.pack(side="left", padx=int(10 * scale_x))

fields["quantity"] = quantity_entry
fields["unit"] = unit_dropdown

create_field("Quantity:", None, 3, inline_widget=quantity_frame)
create_field("Shift:", "shift", 4, is_dropdown=True)
create_field("Reason:", "reason", 5)
create_field("Additional Comments:", "comments", 6, is_textbox=True)

# --- SCADA Import Function ---
def import_scada_report():
    try:
        file_path = filedialog.askopenfilename(
            title="Select SCADA Report",
            filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if not file_path:
            return

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
        fields["unit"].set(get_value("unit", "measurement unit", default="lb"))
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
    unit = fields["unit"].get().strip()
    shift = fields["shift"].get().strip()
    reason = fields["reason"].get().strip()
    comments = fields["comments"].get("1.0", tk.END).strip()

    if not machine_operator or not date or not quantity or shift == "Select Shift" or not unit:
        messagebox.showerror("Validation Error", "Please fill in all required fields.")
        return

    try:
        quantity = float(quantity)
    except ValueError:
        messagebox.showerror("Validation Error", "Quantity must be a number.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrap_logs (machine_operator, date, quantity, unit, shift, reason, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (machine_operator, date, quantity, unit, shift, reason, comments))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Scrap entry saved successfully!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Duplicate Entry", "An entry for this operator and date already exists.")
    except Exception as e:
        messagebox.showerror("Database Error", f"An error occurred: {e}")

# --- Buttons ---
style.configure("Green.TButton",
                background="#22C55E", foreground="white",
                font=("Segoe UI", int(16 * scale_font), "bold"),
                padding=int(10 * scale_y))
style.map("Green.TButton", background=[("active", "#16A34A")])

ttk.Button(main_frame, text="Submit Scrap Entry", style="Green.TButton",
           cursor="hand2", command=submit_scrap_entry).pack(pady=int(30 * scale_y), ipady=int(5 * scale_y))

root.mainloop()
