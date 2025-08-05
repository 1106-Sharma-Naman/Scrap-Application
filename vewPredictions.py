import tkinter as tk
from tkinter import ttk
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# --- Colors ---
COLOR_BG = "#F4F6F8"
CARD_COLORS = ["#27AE60", "#E67E22", "#5DADE2", "#229954"]

# --- Root Window ---
root = tk.Tk()
root.title("View Predictions")
root.configure(bg=COLOR_BG)
root.state("zoomed")  # Fullscreen on all OS

# Responsive grid
for i in range(5):
    root.rowconfigure(i, weight=1)
root.columnconfigure(0, weight=1)

# --- Top Bar ---
top_frame = tk.Frame(root, bg=COLOR_BG, pady=10)
top_frame.grid(row=0, column=0, sticky="ew")
top_frame.columnconfigure(0, weight=1)

title_label = tk.Label(top_frame, text="View Predictions", font=("Arial", 28, "bold"), bg=COLOR_BG)
title_label.grid(row=0, column=0, sticky="w", padx=20)

date_label = tk.Label(top_frame, text=datetime.now().strftime("%A, %B %d, %Y"),
                      font=("Arial", 12), bg=COLOR_BG)
date_label.grid(row=0, column=1, sticky="e", padx=20)

# --- KPI Cards ---
card_frame = tk.Frame(root, bg=COLOR_BG)
card_frame.grid(row=1, column=0, sticky="ew", pady=5)
for i in range(4):
    card_frame.columnconfigure(i, weight=1)

card_texts = [
    ("Prediction Accuracy", "92.3%"),
    ("Forecasted Scrap", "1,820 lbs"),
    ("Top Scrap Factor", "3,700"),
    ("Highest Risk Shift", "Night Shift")
]

for i, (title, value) in enumerate(card_texts):
    frame = tk.Frame(card_frame, bg=CARD_COLORS[i], height=100)
    frame.grid(row=0, column=i, padx=5, sticky="nsew")
    frame.grid_propagate(False)
    tk.Label(frame, text=title, font=("Arial", 14, "bold"),
             bg=CARD_COLORS[i], fg="white").pack(pady=(10, 0))
    tk.Label(frame, text=value, font=("Arial", 18, "bold"),
             bg=CARD_COLORS[i], fg="white").pack()

# --- Filters ---
filter_frame = tk.Frame(root, bg=COLOR_BG)
filter_frame.grid(row=2, column=0, sticky="ew", pady=5)
filter_frame.columnconfigure((0, 1, 2), weight=1)

ttk.Combobox(filter_frame, values=["Weekly", "Monthly"], state="readonly").grid(row=0, column=0, padx=5)
ttk.Combobox(filter_frame, values=["Machine", "Shift"], state="readonly").grid(row=0, column=1, padx=5)
ttk.Button(filter_frame, text="Compare").grid(row=0, column=2, padx=5)

# --- Middle Section (Chart + Pie Chart) ---
middle_frame = tk.Frame(root, bg=COLOR_BG)
middle_frame.grid(row=3, column=0, sticky="nsew")
middle_frame.columnconfigure(0, weight=3)
middle_frame.columnconfigure(1, weight=2)
middle_frame.rowconfigure(0, weight=1)

# Forecast scrap chart
fig1, ax1 = plt.subplots(figsize=(5, 3), dpi=100)
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
scrap_values = [20, 28, 28, 40, 50, 60, 75, 100]
ax1.plot(months, scrap_values, marker="o", color="#3498DB")
ax1.fill_between(months, scrap_values, alpha=0.1, color="#3498DB")
ax1.set_title("Forecast scrap amount")
ax1.set_ylabel("Scrap (lbs)")
ax1.grid(True)

canvas1 = FigureCanvasTkAgg(fig1, master=middle_frame)
canvas1.draw()
canvas1.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

# Pie chart for Scrap Causes
fig2, ax2 = plt.subplots(figsize=(4, 4), dpi=100)
causes = [("Machine Misalignment", 55), ("Tool Wear", 27), ("Material Defect", 18)]
labels = [c[0] for c in causes]
sizes = [c[1] for c in causes]
colors = ["#3498DB", "#E67E22", "#2ECC71"]

ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
ax2.axis('equal')  # Equal aspect ratio

canvas2 = FigureCanvasTkAgg(fig2, master=middle_frame)
canvas2.draw()
canvas2.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

# --- Recommendations ---
rec_frame = tk.Frame(root, bg="white", bd=1, relief="solid", padx=10, pady=10)
rec_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)
tk.Label(rec_frame, text="Recommendations", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")

recommendations = [
    "Schedule alignment check for Machine 4",
    "Adjust speed for night shift to minimize tool wear",
    "Evaluate material supplier A for quality issues"
]
for rec in recommendations:
    tk.Label(rec_frame, text=f"• {rec}", font=("Arial", 12), bg="white").pack(anchor="w", pady=2)

root.mainloop()
