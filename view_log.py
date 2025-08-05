import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk
from datetime import datetime
import psycopg2
import os
import platform

# --- PostgreSQL Connection ---
def get_db_connection():
    return psycopg2.connect(
        dbname="scrapsense",
        user="postgres",
        password="",
        host="localhost",
        port="5432"
    )

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# --- Window ---
root = tk.Tk()
root.title("ScrapSense - View Scrap Logs")
root.configure(bg="#F8FAFC")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Scaling
scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

if platform.system() == "Windows":
    root.tk.call('tk', 'scaling', 1.25)

# --- Load icons ---
def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(path):
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    return None

calendar_icon = load_icon("schedules.jpg", (int(20 * scale_x), int(20 * scale_y)))

# --- Calendar Picker ---
def open_calendar(entry_widget):
    top = tk.Toplevel(root)
    top.title("Select Date")
    cal = Calendar(top, selectmode="day", year=datetime.now().year,
                   month=datetime.now().month, day=datetime.now().day)
    cal.pack(pady=20)

    def pick_date():
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, cal.get_date())
        top.destroy()

    ttk.Button(top, text="Select", command=pick_date).pack(pady=10)

# --- Placeholder Support ---
def add_placeholder(entry, placeholder):
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

# --- Tooltip ---
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

# --- Sidebar ---
sidebar_width = int(80 * scale_x)
sidebar = tk.Frame(root, bg="#1E293B", width=sidebar_width)
sidebar.pack(side="left", fill="y")

logo_img = load_icon("scraplogo.png", (int(50 * scale_x), int(50 * scale_y)))
if logo_img:
    logo_label = tk.Label(sidebar, image=logo_img, bg="#1E293B")
    logo_label.pack(pady=int(30 * scale_y))

nav_items = [
    ("dashboard.png", "Dashboard"),
    ("add-button.png", "Add Scrap"),
    ("doc.png", "View Logs"),
    ("report-card.png", "Reports"),
    ("setting.png", "Settings")
]

for icon_path, tooltip_text in nav_items:
    icon_img = load_icon(icon_path, (int(30 * scale_x), int(30 * scale_y)))
    if icon_img:
        btn = tk.Label(sidebar, image=icon_img, bg="#1E293B", width=sidebar_width, height=int(60 * scale_y))
        btn.image = icon_img
        btn.pack(pady=int(5 * scale_y))
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#334155"))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#1E293B"))
        create_tooltip(btn, tooltip_text)

# --- Main Frame ---
main_frame = tk.Frame(root, bg="#F8FAFC")
main_frame.pack(side="left", fill="both", expand=True)

# Title
tk.Label(main_frame, text="Scrap Logs",
         font=("Segoe UI", int(36 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").pack(pady=int(20 * scale_y))

# --- Filter Frame ---
filter_frame = tk.Frame(main_frame, bg="#F8FAFC")
filter_frame.pack(pady=int(10 * scale_y))

tk.Label(filter_frame, text="Machine Operator:", font=("Segoe UI", int(12 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=int(10 * scale_x))
operator_entry = tk.Entry(filter_frame, font=("Segoe UI", int(12 * scale_font)), width=20, bg="white")
operator_entry.grid(row=0, column=1, padx=int(10 * scale_x))
add_placeholder(operator_entry, "Search Operator")

tk.Label(filter_frame, text="Shift:", font=("Segoe UI", int(12 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").grid(row=0, column=2, padx=int(10 * scale_x))
shift_combo = ttk.Combobox(filter_frame, values=["All", "Morning", "Afternoon", "Night"],
                           font=("Segoe UI", int(12 * scale_font)), width=15)
shift_combo.set("All")
shift_combo.grid(row=0, column=3, padx=int(10 * scale_x))

tk.Label(filter_frame, text="From Date:", font=("Segoe UI", int(12 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").grid(row=0, column=4, padx=int(10 * scale_x))
from_date = tk.Entry(filter_frame, font=("Segoe UI", int(12 * scale_font)), width=15, bg="white")
from_date.grid(row=0, column=5)
add_placeholder(from_date, "MM/DD/YYYY")
if calendar_icon:
    tk.Button(filter_frame, image=calendar_icon, bg="white", bd=0,
              command=lambda: open_calendar(from_date)).grid(row=0, column=6, padx=int(5 * scale_x))

tk.Label(filter_frame, text="To Date:", font=("Segoe UI", int(12 * scale_font), "bold"),
         bg="#F8FAFC", fg="#0F172A").grid(row=0, column=7, padx=int(10 * scale_x))
to_date = tk.Entry(filter_frame, font=("Segoe UI", int(12 * scale_font)), width=15, bg="white")
to_date.grid(row=0, column=8)
add_placeholder(to_date, "MM/DD/YYYY")
if calendar_icon:
    tk.Button(filter_frame, image=calendar_icon, bg="white", bd=0,
              command=lambda: open_calendar(to_date)).grid(row=0, column=9, padx=int(5 * scale_x))

# --- Table ---
table_frame = tk.Frame(main_frame, bg="#F8FAFC")
table_frame.pack(fill="both", expand=True, padx=int(20 * scale_x), pady=int(20 * scale_y))

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
                background="white", foreground="black", fieldbackground="white",
                rowheight=int(35 * scale_y), font=("Segoe UI", int(12 * scale_font)))
style.map("Treeview", background=[("selected", "#3E84FB")], foreground=[("selected", "white")])
style.configure("Treeview.Heading", background="#F1F5F9", foreground="black",
                font=("Segoe UI", int(12 * scale_font), "bold"))

columns = ("id", "machine_operator", "date", "quantity", "unit", "shift", "reason", "comments")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
for col in columns:
    tree.heading(col, text=col.replace("_", " ").title())
    tree.column(col, width=int(150 * scale_x), anchor="center")
tree.pack(fill="both", expand=True)

# --- Fetch Data ---
def fetch_data():
    conn = get_db_connection()
    c = conn.cursor()

    query = "SELECT * FROM scrap_logs WHERE 1=1"
    params = []

    if operator_entry.get().strip() and operator_entry.get() != "Search Operator":
        query += " AND machine_operator ILIKE %s"
        params.append(f"%{operator_entry.get().strip()}%")

    if shift_combo.get() != "All":
        query += " AND shift = %s"
        params.append(shift_combo.get())

    if from_date.get().strip() and from_date.get() != "MM/DD/YYYY":
        query += " AND date >= %s"
        params.append(from_date.get().strip())

    if to_date.get().strip() and to_date.get() != "MM/DD/YYYY":
        query += " AND date <= %s"
        params.append(to_date.get().strip())

    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()

    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", tk.END, values=row)

# --- Buttons ---
btn_frame = tk.Frame(main_frame, bg="#F8FAFC")
btn_frame.pack(pady=int(10 * scale_y))

ttk.Button(btn_frame, text="Search", command=fetch_data).grid(row=0, column=0, padx=5)
ttk.Button(btn_frame, text="Refresh", command=lambda: [
    operator_entry.delete(0, tk.END), add_placeholder(operator_entry, "Search Operator"),
    shift_combo.set("All"),
    from_date.delete(0, tk.END), add_placeholder(from_date, "MM/DD/YYYY"),
    to_date.delete(0, tk.END), add_placeholder(to_date, "MM/DD/YYYY"),
    fetch_data()
]).grid(row=0, column=1, padx=5)

fetch_data()
root.mainloop()
