import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # For logo image

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

# Create main window
root = tk.Tk()
root.title("Login Page")
root.geometry("800x600")
root.configure(bg="white")

# Center frame with padding and thinner border
container = tk.Frame(
    root,
    bg="#f0f0f0",
    bd=1,                       # Reduced from 2 to 1
    relief="solid",
    highlightbackground="darkblue",
    highlightthickness=0        # Reduced from 1 to 0
)
container.place(relx=0.5, rely=0.5, anchor="center", width=500, height=500)

# Add logo image (or fallback text)
try:
    image = Image.open("logo.png")  # Replace with your image path
    image = image.resize((100, 100))
    logo = ImageTk.PhotoImage(image)
    logo_label = tk.Label(container, image=logo, bg="#f0f0f0")
    logo_label.image = logo
    logo_label.pack(pady=(20, 10))
except:
    logo_label = tk.Label(container, text="Your Logo", font=("Arial", 16, "bold"), bg="#f0f0f0")
    logo_label.pack(pady=(20, 10))

# Fonts
label_font = ("Helvetica", 12)
entry_font = ("Helvetica", 12)

# Username
tk.Label(container, text="Username", font=label_font, bg="#f0f0f0").pack(pady=(10, 0))
username_entry = tk.Entry(container, font=entry_font, width=30, relief="groove", bd=2)
username_entry.pack(ipady=8, pady=5)

# Company ID
tk.Label(container, text="Company ID", font=label_font, bg="#f0f0f0").pack(pady=(10, 0))
company_id_entry = tk.Entry(container, font=entry_font, width=30, relief="groove", bd=2)
company_id_entry.pack(ipady=8, pady=5)

# Password
tk.Label(container, text="Password", font=label_font, bg="#f0f0f0").pack(pady=(10, 0))
password_entry = tk.Entry(container, font=entry_font, width=30, relief="groove", bd=2, show="*")
password_entry.pack(ipady=8, pady=5)

# Login Button with soft color and hover effect
def on_login_hover(e):
    login_btn.config(bg="#3498DB")  # Darker blue on hover

def on_login_leave(e):
    login_btn.config(bg="#5DADE2")  # Original soft blue

login_btn = tk.Button(
    container,
    text="Login",
    font=("Helvetica", 13, "bold"),
    bg="#3E84FB",         # Soft blue
    fg="white",           # White text
    activebackground="#3498DB",
    activeforeground="white",
    width=20,
    relief="flat",
    bd=0,
    command=login
)
login_btn.pack(pady=20, ipadx=5, ipady=5)
login_btn.bind("<Enter>", on_login_hover)
login_btn.bind("<Leave>", on_login_leave)

# Forgot Password link
forgot_label = tk.Label(container, text="Forgot Password?", font=("Helvetica", 10, "underline"),
                        fg="blue", cursor="hand2", bg="#f0f0f0")
forgot_label.pack()
forgot_label.bind("<Button-1>", lambda e: forgot_password())

# Start GUI loop
root.mainloop()
