import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import os

BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")

def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    img = Image.open(path).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


class DashboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#E6EBEF")
        self.controller = controller

        self.scale_x = self.winfo_screenwidth() / 1920
        self.scale_y = self.winfo_screenheight() / 1080
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.build_interface()

    def build_interface(self):
        username = "Akshay"
        # Welcome text
        tk.Label(self,
                 text=f"Welcome, {username}",
                 font=("Segoe UI", int(24 * self.scale_font), "bold"),
                 bg="#E6EBEF", fg="#1F3B4D").place(
            x=int(100 * self.scale_x), y=int(50 * self.scale_y))

        # Clock
        self.time_label = tk.Label(self,
                                   font=("Segoe UI", int(14 * self.scale_font)),
                                   bg="#E6EBEF", fg="#1F3B4D")
        self.time_label.place(relx=0.98, y=int(40 * self.scale_y), anchor="ne")
        self.update_time()

        # Dashboard heading
        tk.Label(self, text="Dashboard",
                 font=("Segoe UI", int(48 * self.scale_font), "bold"),
                 bg="#E6EBEF", fg="#1F3B4D").pack(
            pady=(int(80 * self.scale_y), int(30 * self.scale_y)))

        # KPI container
        kpi_frame = tk.Frame(self, bg="#E6EBEF")
        kpi_frame.pack(pady=(0, int(40 * self.scale_y)))

        self.create_kpi_card(kpi_frame, "reduce-cost.png", "Today's Scrap", "120 lbs", "#F6A96D", 0)
        self.create_kpi_card(kpi_frame, "dollar-sign.png", "This Week's Scrap Cost", "$4,200", "#86EFAC", 1)
        self.create_kpi_card(kpi_frame, "warning-triangle.png", "Top Cause", "Machine Misalign", "#FF7F7F", 2)
        self.create_kpi_card(kpi_frame, "predictive-chart.png", "Predicted End-of-Month", "3,200 lbs", "#7DD3FC", 3)

        # Button cards
        button_frame = tk.Frame(self, bg="#E6EBEF")
        button_frame.pack()

        self.create_button_card(button_frame, "Add Scrap", "add-button.png", 0, 0)
        self.create_button_card(button_frame, "View Predictions", "prediction.png", 0, 1)
        self.create_button_card(button_frame, "View Scrap Logs", "doc.png", 1, 0)
        self.create_button_card(button_frame, "Generate Report", "report-card.png", 1, 1)

    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
        self.after(1000, self.update_time)

    def create_kpi_card(self, parent, icon_file, title, value, color, column):
        """Create a single KPI Card with balanced vertical spacing."""
        icon = load_icon(icon_file, (int(50 * self.scale_x), int(50 * self.scale_y)))

        card = tk.Frame(parent,
                        bg=color,
                        width=int(320 * self.scale_x),
                        height=int(175 * self.scale_y),
                        highlightthickness=1,
                        highlightbackground="#CCCCCC")
        card.grid(row=0, column=column, padx=int(30 * self.scale_x))
        card.pack_propagate(False)  # keep fixed size

        # Icon
        tk.Label(card, image=icon, bg=color).pack(pady=(int(10 * self.scale_y), int(5 * self.scale_y)))

        # Title
        tk.Label(card,
                 text=title,
                 font=("Segoe UI", int(18 * self.scale_font), "bold"),
                 bg=color,
                 fg="white",
                 anchor="center",
                 justify="center").pack(pady=(0, 5), fill='x')

        # Value
        tk.Label(card,
                 text=value,
                 font=("Segoe UI", int(22 * self.scale_font), "bold"),
                 bg=color,
                 fg="white",
                 anchor="center",
                 justify="center").pack(fill='both', expand=True, pady=(0, 15))

        card.image = icon  # Keep reference

    def create_button_card(self, parent, text, icon_file, row, column):
        """Create a big clickable button card."""
        icon = load_icon(icon_file, (int(30 * self.scale_x), int(30 * self.scale_y)))

        btn_card = tk.Frame(parent,
                            bg="white",
                            width=int(350 * self.scale_x),
                            height=int(150 * self.scale_y),
                            highlightthickness=1,
                            highlightbackground="#D0D7DE")
        btn_card.grid(row=row, column=column,
                      padx=int(40 * self.scale_x),
                      pady=int(20 * self.scale_y))
        btn_card.pack_propagate(False)

        btn = tk.Button(btn_card,
                        text=f"  {text}",
                        image=icon,
                        compound="left",
                        font=("Segoe UI", int(20 * self.scale_font), "bold"),
                        bg="white",
                        fg="#1F3B4D",
                        relief="flat",
                        bd=0,
                        activebackground="#E6EBEF",
                        padx=int(20 * self.scale_x),
                        pady=int(10 * self.scale_y),
                        command=lambda: self.controller.show_frame(text))
        btn.pack(expand=True, fill="both")
        btn.bind("<Enter>", lambda e: btn.config(bg="#F1F3F4", relief="solid", bd=2))
        btn.bind("<Leave>", lambda e: btn.config(bg="white", relief="flat", bd=0))
        btn.image = icon
