import tkinter as tk
from tkinter import messagebox
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

# Initialize main window
root = tk.Tk()
root.title("Login Page")
root.configure(bg="white")

# Get screen width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Set window size to 60% of screen dimensions
window_width = int(screen_width * 0.6)
window_height = int(screen_height * 0.6)

# Center window on screen
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Adjust scaling for high DPI
try:
    root.tk.call('tk', 'scaling', screen_width / 1920)
except:
    pass

# Fonts scaled according to screen size
base_font_size = int(window_width * 0.015)
entry_font_size = int(base_font_size * 0.9)
button_font_size = int(base_font_size * 0.9)

# Main frame
container = tk.Frame(
    root,
    bg="#f9f9f9",
    bd=1,
    relief="solid",
    highlightbackground="gray",
    highlightthickness=0
)
container.place(relx=0.5, rely=0.5, anchor="center", width=window_width * 0.5, height=window_height * 0.85)

# Load logo or fallback
try:
    image = Image.open("logo.png")
    image = image.resize((100, 100))
    logo = ImageTk.PhotoImage(image)
    logo_label = tk.Label(container, image=logo, bg="#f9f9f9")
    logo_label.image = logo
    logo_label.pack(pady=(20, 10))
except:
    logo_label = tk.Label(container, text="Your Logo", font=("Arial", base_font_size), bg="#f9f9f9")
    logo_label.pack(pady=(20, 10))

label_font = ("Helvetica", base_font_size)
entry_font = ("Helvetica", entry_font_size)

entry_config = {
    "font": entry_font,
    "width": 30,
    "relief": "solid",
    "bd": 1,
    "bg": "white",
    "fg": "black",
    "insertbackground": "black",
    "highlightthickness": 1,
    "highlightbackground": "#ccc",
    "highlightcolor": "#3E84FB"
}

# Username
tk.Label(container, text="Username", font=label_font, bg="#f9f9f9", fg="black").pack(pady=(10, 0))
username_entry = tk.Entry(container, **entry_config)
username_entry.pack(ipady=6, pady=5)

# Company ID
tk.Label(container, text="Company ID", font=label_font, bg="#f9f9f9", fg="black").pack(pady=(10, 0))
company_id_entry = tk.Entry(container, **entry_config)
company_id_entry.pack(ipady=6, pady=5)

# Password
tk.Label(container, text="Password", font=label_font, bg="#f9f9f9", fg="black").pack(pady=(10, 0))
password_entry = tk.Entry(container, **entry_config, show="*")
password_entry.pack(ipady=6, pady=5)

# Login Button
def on_login_hover(e):
    login_btn.config(bg="#3498DB")

def on_login_leave(e):
    login_btn.config(bg="#3E84FB")

login_btn = tk.Button(
    container,
    text="Login",
    font=("Helvetica", button_font_size, "bold"),
    bg="#3E84FB",
    fg="white",
    activebackground="#3498DB",
    activeforeground="white",
    width=20,
    relief="flat",
    bd=0,
    command=login
)
login_btn.pack(pady=20, ipadx=5, ipady=6)
login_btn.bind("<Enter>", on_login_hover)
login_btn.bind("<Leave>", on_login_leave)

# Forgot Password
forgot_label = tk.Label(
    container,
    text="Forgot Password?",
    font=("Helvetica", int(button_font_size * 0.8), "underline"),
    fg="blue",
    cursor="hand2",
    bg="#f9f9f9"
)
forgot_label.pack()
forgot_label.bind("<Button-1>", lambda e: forgot_password())

root.mainloop()
