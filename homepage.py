from tkinter import *
from PIL import Image, ImageTk
import os

# Initialize
root = Tk()
root.title("ScrapSense Dashboard")
root.state("zoomed")  # Full screen
root.configure(bg="white")

# Load logo (transparent PNG)
logo_path = os.path.join(os.path.dirname(__file__), "scrap_sense_logo.png")
logo_img = Image.open(logo_path).resize((100, 100), Image.Resampling.LANCZOS)
logo_img = ImageTk.PhotoImage(logo_img)

# ---------- HEADER ----------
header_frame = Frame(root, bg="white")
header_frame.pack(pady=20)

logo_label = Label(header_frame, image=logo_img, bg="white")
logo_label.pack()

# ---------- BUTTON STYLE ----------
def create_dashboard_button(parent, icon_text, label, command=None):
    btn = Frame(parent, bg="white", highlightthickness=1, highlightbackground="#ccc")
    btn.pack_propagate(False)

    label_icon = Label(btn, text=icon_text, font=("Arial", 28), bg="white", fg="#1B2A41")
    label_icon.pack(pady=(15, 5))

    label_text = Label(btn, text=label, font=("Arial", 16, "bold"), bg="white", fg="#1B2A41")
    label_text.pack()

    btn.bind("<Enter>", lambda e: btn.config(bg="#f0f0f0"))
    btn.bind("<Leave>", lambda e: btn.config(bg="white"))
    if command:
        btn.bind("<Button-1>", lambda e: command())

    return btn

# ---------- DASHBOARD ----------
dashboard_frame = Frame(root, bg="white")
dashboard_frame.pack(expand=True, fill="both", pady=20)

buttons = [
    ("➕", "Add Scrap"),
    ("📈", "View Predictions"),
    ("📄", "View Scrap Logs"),
    ("📊", "Generate Report"),
    ("⚙", "Settings"),
    ("📦", "Inventory"),
]

rows, cols = 3, 2
index = 0
for r in range(rows):
    for c in range(cols):
        if index < len(buttons):
            icon, text = buttons[index]
            btn = create_dashboard_button(dashboard_frame, icon, text)
            btn.grid(row=r, column=c, padx=40, pady=30, sticky="nsew")
            index += 1

# Expand to fill screen
for i in range(cols):
    dashboard_frame.grid_columnconfigure(i, weight=1)
for i in range(rows):
    dashboard_frame.grid_rowconfigure(i, weight=1)

# ---------- FOOTER ----------
footer_label = Label(root, text="© 2025 ScrapSense - All Rights Reserved",
                     bg="white", fg="gray", font=("Arial", 12))
footer_label.pack(side=BOTTOM, pady=10)

root.mainloop()
