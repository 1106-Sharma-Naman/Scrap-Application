import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

def login():
    username = username_entry.get()
    company_id = company_id_entry.get()
    password = password_entry.get()
    if username and company_id and password:
        messagebox.showinfo("Login", "Login successful!")
    else:
        messagebox.showwarning("Login", "Please fill in all fields.")

def forgot_password():
    messagebox.showinfo("Forgot Password", "Password reset link sent to your email (not really).")

# --- Window ---
root = tk.Tk()
root.title("Login Page")
root.configure(bg="white")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Scaling
scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

def scaled_font(name, size, weight="normal"):
    return (name, max(8, int(size * scale_font)), weight)

# --- ttk Styles ---
style = ttk.Style()
style.theme_use("clam")  # Forces a consistent theme

style.configure(
    "Blue.TButton",
    font=scaled_font("Helvetica", 13, "bold"),
    background="#3E84FB",
    foreground="white",
    padding=(10, 5)
)
style.map(
    "Blue.TButton",
    background=[("active", "#3498DB"), ("pressed", "#2d6fa3")],
    foreground=[("active", "white"), ("pressed", "white")]
)

# --- Container ---
container_width = int(500 * scale_x)
container_height = int(500 * scale_y)
container = tk.Frame(root, bg="#f0f0f0", highlightbackground="#ccc", highlightthickness=1)
container.place(relx=0.5, rely=0.5, anchor="center", width=container_width, height=container_height)

# --- Logo ---
try:
    image = Image.open("logo.png")
    image = image.resize((int(100 * scale_x), int(100 * scale_y)))
    logo = ImageTk.PhotoImage(image)
    logo_label = tk.Label(container, image=logo, bg="#f0f0f0")
    logo_label.image = logo
    logo_label.pack(pady=(int(20 * scale_y), int(10 * scale_y)))
except:
    tk.Label(container, text="Your Logo", font=scaled_font("Arial", 16, "bold"),
             bg="#f0f0f0", fg="black").pack(pady=(int(20 * scale_y), int(10 * scale_y)))

# --- Input creator ---
def create_input(label_text, show=None):
    tk.Label(container, text=label_text, font=scaled_font("Helvetica", 12), bg="#f0f0f0", fg="black")\
        .pack(pady=(int(10 * scale_y), 0))
    entry = tk.Entry(container, font=scaled_font("Helvetica", 12), width=30,
                     relief="solid", bd=1, show=show,
                     bg="white", fg="black", insertbackground="black",
                     highlightthickness=1, highlightbackground="#ccc", highlightcolor="#2563EB")
    entry.pack(ipady=int(8 * scale_y), pady=int(5 * scale_y))
    return entry

username_entry = create_input("Username")
company_id_entry = create_input("Company ID")
password_entry = create_input("Password", show="*")

# --- Login Button (ttk) ---
login_btn = ttk.Button(container, text="Login", style="Blue.TButton", command=login)
login_btn.pack(pady=int(20 * scale_y))

# --- Forgot password ---
forgot_label = tk.Label(container, text="Forgot Password?",
                        font=scaled_font("Helvetica", 10),
                        fg="blue", cursor="hand2", bg="#f0f0f0")
forgot_label.pack()
forgot_label.bind("<Button-1>", lambda e: forgot_password())

root.mainloop()
