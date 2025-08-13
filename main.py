import tkinter as tk
from PIL import Image, ImageTk
import os

from dashboard import DashboardFrame
from view_log import ViewLogFrame
from addscrap import AddScrapFrame

# ---- Import the predictions frame (supports either class name) ----
try:
    from view_predictions import ViewPredictionsFrame
except ImportError:
    from view_predictions import PredictionsDashboardFrame as ViewPredictionsFrame

# ---- Import Generate Report frame ----
GENERATE_REPORT_AVAILABLE = True
try:
    from generate_report import GenerateReportFrame
except Exception:
    GenerateReportFrame = None
    GENERATE_REPORT_AVAILABLE = False

# --- Paths ---
BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# --- Function to Load Icons ---
def load_icon(filename, size):
    path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    img = Image.open(path).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

# --- Tooltip Helper Class ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None

    def showtip(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#333333", foreground="white",
            relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 10, "normal"),
            padx=5, pady=3
        )
        label.pack()

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

# --- App Setup ---
class ScrapSenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ScrapSense")
        self.configure(bg="#F8FAFC")

        # Try to maximize cross-platform
        try:
            self.state("zoomed")  # Windows/Linux
        except Exception:
            try:
                self.attributes("-zoomed", True)  # some *nix
            except Exception:
                sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                self.geometry(f"{int(sw*0.9)}x{int(sh*0.9)}+40+40")

        self.frames = {}
        self.sidebar_icons = {}

        self._build_sidebar()
        self._build_container()
        self.show_frame("Dashboard")

    def _build_sidebar(self):
        scale_x = max(self.winfo_screenwidth() / 1920, 0.75)
        scale_y = max(self.winfo_screenheight() / 1080, 0.75)

        sidebar = tk.Frame(self, bg="#1F3B4D", width=int(80 * scale_x))
        sidebar.pack(side="left", fill="y")

        # Logo
        try:
            logo_img = load_icon("scraplogo.png", (int(50 * scale_x), int(50 * scale_y)))
            logo_label = tk.Label(sidebar, image=logo_img, bg="#1F3B4D")
            logo_label.image = logo_img
            logo_label.pack(pady=int(30 * scale_y))
        except FileNotFoundError:
            tk.Label(sidebar, text="ScrapSense", fg="white", bg="#1F3B4D",
                     font=("Segoe UI", 14, "bold")).pack(pady=int(30 * scale_y))

        # Sidebar buttons (icons)
        buttons = [
            ("Dashboard", "dashboard.png"),
            ("Add Scrap", "add-button.png"),
            ("View Predictions", "prediction.png"),
            ("View Scrap Logs", "doc.png"),
            ("Generate Report", "report-card.png"),
            ("Settings", "setting.png"),
        ]

        def hover_on(widget):
            widget.config(bg="#2D4F64")

        def hover_off(widget):
            widget.config(bg="#1F3B4D")

        for name, icon_file in buttons:
            try:
                icon = load_icon(icon_file, (int(30 * scale_x), int(30 * scale_y)))
            except FileNotFoundError:
                icon = None

            btn = tk.Label(
                sidebar, image=icon, bg="#1F3B4D",
                width=int(80 * scale_x), height=int(60 * scale_y),
                text=("" if icon else name), compound="top", fg="white", font=("Segoe UI", 9)
            )
            if icon:
                btn.image = icon
            btn.pack(pady=int(5 * scale_y))

            btn.bind("<Button-1>", lambda e, n=name: self.show_frame(n))

            tooltip = Tooltip(btn, name)
            btn.bind("<Enter>", lambda e, b=btn, t=tooltip: (hover_on(b), t.showtip()))
            btn.bind("<Leave>", lambda e, b=btn, t=tooltip: (hover_off(b), t.hidetip()))

    def _build_container(self):
        container = tk.Frame(self, bg="#F8FAFC")
        container.pack(side="left", expand=True, fill="both")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # --- Instantiate frames ---
        self.frames["Dashboard"] = DashboardFrame(container, self)
        self.frames["Add Scrap"] = AddScrapFrame(container, self)
        self.frames["View Scrap Logs"] = ViewLogFrame(container, self)
        self.frames["View Predictions"] = ViewPredictionsFrame(container, self)

        # Generate Report frame (if available)
        if GENERATE_REPORT_AVAILABLE and GenerateReportFrame is not None:
            self.frames["Generate Report"] = GenerateReportFrame(container, self)
        else:
            # Placeholder frame that shows a message if clicked
            placeholder = tk.Frame(container, bg="#F8FAFC")
            msg = tk.Label(
                placeholder,
                text="Generate Report is not available.\nMake sure generate_report.py is present and imports correctly.",
                bg="#F8FAFC", fg="#0E2A47", font=("Segoe UI", 14, "bold")
            )
            msg.pack(expand=True)
            self.frames["Generate Report"] = placeholder

        # Place all frames
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, name):
        frame = self.frames.get(name)
        if frame:
            frame.tkraise()
        else:
            try:
                import tkinter.messagebox as messagebox
                messagebox.showwarning("Coming soon", f"'{name}' page is not implemented yet.")
            except Exception:
                pass

if __name__ == "__main__":
    app = ScrapSenseApp()
    app.mainloop()
