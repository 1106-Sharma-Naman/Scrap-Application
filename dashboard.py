import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import os

# --- Base Paths ---
BASE_DIR = os.path.dirname(__file__)        # directory where script is
IMAGE_DIR = os.path.join(BASE_DIR, "images") # images folder in repo

# --- Function to Load Icons ---
def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    img = Image.open(path).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

# --- Window Setup ---
root = tk.Tk()
root.title("ScrapSense Dashboard")
root.configure(bg="#E6EBEF")

# Detect screen size and scaling factor
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Scale factors relative to base 1920x1080 design
scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

# --- Function to Update Time ---
def update_time():
    now = datetime.now()
    current_time = now.strftime("%A, %B %d, %Y  %I:%M:%S %p")
    time_label.config(text=current_time)
    root.after(1000, update_time)

# --- Sidebar Frame (Slim) ---
sidebar_width = int(80 * scale_x)
sidebar = tk.Frame(root, bg="#1F3B4D", width=sidebar_width)
sidebar.pack(side="left", fill="y")

# --- Sidebar Logo ---
logo_tk = load_icon("scraplogo.png", (int(50 * scale_x), int(50 * scale_y)))
logo_label = tk.Label(sidebar, image=logo_tk, bg="#1F3B4D")
logo_label.pack(pady=int(30 * scale_y))

# --- Sidebar Navigation (Icons Only) ---
nav_icons = [
    ("dashboard.png", "Dashboard"),
    ("add-button.png", "Add Scrap"),
    ("prediction.png", "Predictions"),
    ("doc.png", "Scrap Logs"),
    ("report-card.png", "Reports"),
    ("setting.png", "Settings")
]

def on_enter_sidebar(e):
    e.widget.config(bg="#2D4F64")

def on_leave_sidebar(e):
    e.widget.config(bg="#1F3B4D")

for icon_path, tooltip in nav_icons:
    icon_img = load_icon(icon_path, (int(30 * scale_x), int(30 * scale_y)))
    btn = tk.Label(sidebar, image=icon_img, bg="#1F3B4D", width=sidebar_width, height=int(60 * scale_y))
    btn.image = icon_img
    btn.pack(pady=int(5 * scale_y))
    btn.bind("<Enter>", on_enter_sidebar)
    btn.bind("<Leave>", on_leave_sidebar)

# --- Main Content Frame ---
main_frame = tk.Frame(root, bg="#E6EBEF")
main_frame.pack(side="left", fill="both", expand=True)

# --- Welcome Message ---
username = "Akshay"
welcome_label = tk.Label(main_frame, text=f"Welcome, {username}", font=("Segoe UI", int(24 * scale_font), "bold"), bg="#E6EBEF", fg="#1F3B4D")
welcome_label.place(x=int(100 * scale_x), y=int(50 * scale_y))

# --- Update Time ---
time_label = tk.Label(main_frame, font=("Segoe UI", int(14 * scale_font)), bg="#E6EBEF", fg="#1F3B4D")
time_label.place(relx=0.98, y=int(40 * scale_y), anchor="ne")
update_time()

# --- Title ---
title_label = tk.Label(main_frame, text="Dashboard", font=("Segoe UI", int(48 * scale_font), "bold"), bg="#E6EBEF", fg="#1F3B4D")
title_label.pack(pady=(int(80 * scale_y), int(30 * scale_y)))

# --- KPI Stats Frame ---
kpi_frame = tk.Frame(main_frame, bg="#E6EBEF")
kpi_frame.pack(pady=(0, int(40 * scale_y)))

# --- Load KPI Icons ---
today_icon = load_icon("reduce-cost.png", (int(50 * scale_x), int(50 * scale_y)))
week_cost_icon = load_icon("dollar-sign.png", (int(50 * scale_x), int(50 * scale_y)))
cause_icon = load_icon("warning-triangle.png", (int(50 * scale_x), int(50 * scale_y)))
predicted_icon = load_icon("predictive-chart.png", (int(50 * scale_x), int(50 * scale_y)))

def create_kpi_card(parent, icon, title, value, color):
    card = tk.Frame(parent, bg=color, width=int(320 * scale_x), height=int(175 * scale_y), highlightthickness=1, highlightbackground="#CCCCCC")
    card.pack_propagate(False)

    icon_label = tk.Label(card, image=icon, bg=color)
    icon_label.pack(pady=(int(20 * scale_y), 0))

    title_label = tk.Label(card, text=title, font=("Segoe UI", int(14 * scale_font), "bold"), bg=color, fg="white")
    title_label.pack()

    value_label = tk.Label(card, text=value, font=("Segoe UI", int(20 * scale_font), "bold"), bg=color, fg="white")
    value_label.pack()

    return card

today_scrap = create_kpi_card(kpi_frame, today_icon, "Today's Scrap", "120 lbs", "#F6A96D")
week_cost = create_kpi_card(kpi_frame, week_cost_icon, "This Week's Scrap Cost", "$4,200", "light green")
top_cause = create_kpi_card(kpi_frame, cause_icon, "Top Cause", "Machine Misalign", "#FF7F7F")
predicted_scrap = create_kpi_card(kpi_frame, predicted_icon, "Predicted End-of-Month", "3,200 lbs", "light blue")

today_scrap.grid(row=0, column=0, padx=int(30 * scale_x))
week_cost.grid(row=0, column=1, padx=int(30 * scale_x))
top_cause.grid(row=0, column=2, padx=int(30 * scale_x))
predicted_scrap.grid(row=0, column=3, padx=int(30 * scale_x))

# --- Load Button Images ---
plus_icon = load_icon("add-button.png", (int(50 * scale_x), int(50 * scale_y)))
prediction_icon = load_icon("prediction.png", (int(50 * scale_x), int(50 * scale_y)))
log_icon = load_icon("doc.png", (int(50 * scale_x), int(50 * scale_y)))
report_icon = load_icon("report-card.png", (int(50 * scale_x), int(50 * scale_y)))

# --- Frame for Buttons ---
button_frame = tk.Frame(main_frame, bg="#E6EBEF")
button_frame.pack()

# --- Button Hover Effect ---
def on_button_enter(e):
    e.widget.config(bg="#F1F3F4", relief="solid", bd=2)

def on_button_leave(e):
    e.widget.config(bg="white", relief="flat", bd=0)

def create_button_card(text, icon):
    btn_card = tk.Frame(button_frame, bg="white", width=int(350 * scale_x), height=int(150 * scale_y), highlightthickness=1, highlightbackground="#D0D7DE")
    btn_card.pack_propagate(False)

    btn = tk.Button(
        btn_card,
        text=text,
        image=icon,
        compound="left",
        font=("Segoe UI", int(20 * scale_font), "bold"),
        bg="white",
        fg="#1F3B4D",
        relief="flat",
        bd=0,
        activebackground="#E6EBEF",
        width=int(20 * scale_x),
        height=int(4 * scale_y),
        padx=int(20 * scale_x),
        pady=int(10 * scale_y)
    )
    btn.pack(expand=True, fill="both")

    # Bind Hover Effect
    btn.bind("<Enter>", on_button_enter)
    btn.bind("<Leave>", on_button_leave)

    return btn_card

# --- Create Buttons ---
add_scrap_btn = create_button_card("Add Scrap", plus_icon)
view_predictions_btn = create_button_card("View Predictions", prediction_icon)
view_logs_btn = create_button_card("View Scrap Logs", log_icon)
generate_report_btn = create_button_card("Generate Report", report_icon)

add_scrap_btn.grid(row=0, column=0, padx=int(40 * scale_x), pady=int(20 * scale_y))
view_predictions_btn.grid(row=0, column=1, padx=int(40 * scale_x), pady=int(20 * scale_y))
view_logs_btn.grid(row=1, column=0, padx=int(40 * scale_x), pady=int(20 * scale_y))
generate_report_btn.grid(row=1, column=1, padx=int(40 * scale_x), pady=int(20 * scale_y))

root.mainloop()
