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

# Initialize root window
root = tk.Tk()
root.title("Login Page")
root.configure(bg="white")

# Get screen size and set dynamic window size
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = int(screen_width * 0.5)
window_height = int(screen_height * 0.6)
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Apply scaling for high DPI screens
try:
    root.tk.call('tk', 'scaling', screen_width / 1920)
except:
    pass

# ------------------- ttk style -------------------
style = ttk.Style()
style.theme_use("clam")

# Configure styles
style.configure("TEntry",
    padding=6,
    relief="solid",
    borderwidth=1,
    font=("Helvetica", 12)
)

style.configure("TButton",
    font=("Helvetica", 12, "bold"),
    foreground="white",
    background="#3E84FB",
    padding=6
)

style.map("TButton",
    background=[("active", "#3498DB")]
)

# ------------------- Main UI -------------------
container = tk.Frame(root, bg="white")
container.place(relx=0.5, rely=0.5, anchor="center", width=window_width * 0.6, height=window_height * 0.9)

# Logo (fallback if missing)
try:
    img = Image.open("logo.png")
    img = img.resize((100, 100))
    logo_img = ImageTk.PhotoImage(img)
    logo_label = tk.Label(container, image=logo_img, bg="white")
    logo_label.image = logo_img
    logo_label.pack(pady=(10, 5))
except:
    logo_label = tk.Label(container, text="Your Logo", font=("Arial", 16), bg="white")
    logo_label.pack(pady=(10, 5))

# Input fields
def create_labeled_entry(label_text):
    tk.Label(container, text=label_text, font=("Helvetica", 13), bg="white").pack(anchor="w", padx=40, pady=(10, 0))
    entry = ttk.Entry(container, width=30, style="TEntry")
    entry.pack(pady=5, ipady=4)
    return entry

username_entry = create_labeled_entry("Username")
company_id_entry = create_labeled_entry("Company ID")
password_entry = create_labeled_entry("Password")
password_entry.config(show="*")

# Login button
login_button = ttk.Button(container, text="Login", command=login, style="TButton")
login_button.pack(pady=(20, 10), ipadx=10)

# Forgot password link
forgot_label = tk.Label(
    container,
    text="Forgot Password?",
    font=("Helvetica", 11, "underline"),
    fg="blue",
    bg="white",
    cursor="hand2"
)
forgot_label.pack()
forgot_label.bind("<Button-1>", lambda e: forgot_password())

root.mainloop()
