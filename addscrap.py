import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import pandas as pd
import psycopg2
import os

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# --- Database ---
def get_db_connection():
    return psycopg2.connect(
        dbname="scrapsense",
        user="postgres",
        password="",
        host="localhost",
        port="5432"
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrap_logs (
            id SERIAL PRIMARY KEY,
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
    cursor.close()
    conn.close()

init_db()

# --- Duplicate check function ---
def entry_exists(machine_operator, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM scrap_logs WHERE machine_operator = %s AND date = %s
    """, (machine_operator, date))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

# --- Flexible value getter for file imports ---
def get_value(row, *possible_names, default=""):
    for name in possible_names:
        lname = name.lower().replace(" ", "").replace("_", "")
        for col in row.keys():
            c = col.lower().replace(" ", "").replace("_", "")
            if lname == c and pd.notna(row[col]):
                return str(row[col])
    return default

# --- GUI Setup ---
root = tk.Tk()
root.title("ScrapSense - Add Scrap")
root.configure(bg="#F8FAFC")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

fields = {}

def update_time():
    now = datetime.now()
    time_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
    root.after(1000, update_time)

def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except FileNotFoundError:
        return None

def create_tooltip(widget, text):
    tooltip = tk.Toplevel(widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    label = tk.Label(tooltip, text=text, bg="black", fg="white", padx=5, pady=3, relief="solid", borderwidth=1)
    label.pack()

    def show_tooltip(event):
        x = event.widget.winfo_rootx() + event.widget.winfo_width() + 10
        y = event.widget.winfo_rooty() + event.widget.winfo_height() // 2
        tooltip.geometry(f"+{x}+{y}")
        tooltip.deiconify()

    def hide_tooltip(event):
        tooltip.withdraw()

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)

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

def on_enter_sidebar(e):
    e.widget.config(bg="#334155")

def on_leave_sidebar(e):
    e.widget.config(bg="#1E293B")

for icon_path, tooltip in nav_icons:
    icon_img = load_icon(icon_path, (int(30 * scale_x), int(30 * scale_y)))
    btn = tk.Label(sidebar, image=icon_img, bg="#1E293B", width=sidebar_width, height=int(60 * scale_y))
    btn.image = icon_img
    btn.pack(pady=int(5 * scale_y))
    btn.bind("<Enter>", on_enter_sidebar)
    btn.bind("<Leave>", on_leave_sidebar)
    create_tooltip(btn, tooltip)

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

form_frame = tk.Frame(main_frame, bg="white",
                      padx=int(40 * scale_x), pady=int(40 * scale_y),
                      highlightbackground="#E2E8F0", highlightthickness=1)
form_frame.pack(pady=int(20 * scale_y))

style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="white", background="white", foreground="black", padding=int(5 * scale_y))

tk.Label(form_frame, text="Entry Type:", font=("Segoe UI", int(14 * scale_font), "bold"),
         bg="white", fg="#334155").grid(row=0, column=0, sticky="w",
                                        pady=int(12 * scale_y), padx=int(10 * scale_x))

entry_type = ttk.Combobox(form_frame, values=["Manual Entry", "Import Document"],
                          width=int(47 * scale_x), font=("Segoe UI", int(12 * scale_font)))
entry_type.set("Select Entry Type")
entry_type.grid(row=0, column=1, pady=int(12 * scale_y))
fields["entry_type"] = entry_type

def handle_entry_type_change(event):
    if entry_type.get() == "Import Document":
        import_document()

entry_type.bind("<<ComboboxSelected>>", handle_entry_type_change)

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

# --- Enhanced import_document() ---
def import_document():
    try:
        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
        if df.empty:
            messagebox.showwarning("Empty File", "The selected file has no data.")
            return

        df.columns = df.columns.str.strip()  # Clean column names

        inserted, skipped = 0, 0
        last_good = {}
        for _, row in df.iterrows():
            mop = get_value(row, "machine operator id", "operator id", "operator")
            date = get_value(row, "date", default=datetime.now().strftime("%m/%d/%Y"))
            qty = get_value(row, "quantity", "scrap quantity")
            unit = get_value(row, "unit", "measurement unit", default="lb")
            shift = get_value(row, "shift", default="Select Shift")
            reason = get_value(row, "reason", "scrap reason")
            comments = get_value(row, "comments", "notes")

            # Skip empty/incomplete
            if not mop or not date or not qty or shift == "Select Shift" or not unit:
                continue

            if entry_exists(mop, date):
                skipped += 1
                continue

            try:
                qty = float(qty)
            except ValueError:
                continue

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scrap_logs (machine_operator, date, quantity, unit, shift, reason, comments)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (mop, date, qty, unit, shift, reason, comments))
                conn.commit()
                cursor.close()
                conn.close()
                inserted += 1
                last_good = dict(machine_operator=mop, date=date, quantity=qty, unit=unit, shift=shift, reason=reason, comments=comments)
            except psycopg2.errors.UniqueViolation:
                skipped += 1
            except Exception:
                skipped += 1

        # Feedback to user
        message = f"Imported {inserted} records."
        if skipped:
            message += f" Skipped {skipped} duplicate or invalid rows."
        messagebox.showinfo("Import Result", message)

        # Fill UI fields with last imported row
        if inserted > 0 and last_good:
            fields["machine_operator"].delete(0, tk.END)
            fields["machine_operator"].insert(0, last_good["machine_operator"])
            fields["date"].delete(0, tk.END)
            fields["date"].insert(0, last_good["date"])
            fields["quantity"].delete(0, tk.END)
            fields["quantity"].insert(0, last_good["quantity"])
            fields["unit"].set(last_good["unit"])
            fields["shift"].set(last_good["shift"])
            fields["reason"].delete(0, tk.END)
            fields["reason"].insert(0, last_good["reason"])
            fields["comments"].delete("1.0", tk.END)
            fields["comments"].insert("1.0", last_good["comments"])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to import file:\n{e}")

# --- Enhanced submit_scrap_entry() ---
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

    if entry_exists(machine_operator, date):
        messagebox.showerror("Duplicate Entry", "An entry for this operator and date already exists.")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrap_logs (machine_operator, date, quantity, unit, shift, reason, comments)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (machine_operator, date, quantity, unit, shift, reason, comments))
        conn.commit()
        cursor.close()
        conn.close()
        messagebox.showinfo("Success", "Scrap entry saved successfully!")
    except psycopg2.errors.UniqueViolation:
        messagebox.showerror("Duplicate Entry", "An entry for this operator and date already exists.")
    except Exception as e:
        messagebox.showerror("Database Error", f"An error occurred: {e}")

style.configure("Green.TButton",
                background="#22C55E", foreground="white",
                font=("Segoe UI", int(16 * scale_font), "bold"),
                padding=int(10 * scale_y))
style.map("Green.TButton", background=[("active", "#16A34A")])

ttk.Button(main_frame, text="Submit Scrap Entry", style="Green.TButton",
           cursor="hand2", command=submit_scrap_entry).pack(pady=int(30 * scale_y), ipady=int(5 * scale_y))

root.mainloop()
