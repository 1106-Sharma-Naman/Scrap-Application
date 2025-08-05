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

# Create main window
root = tk.Tk()
root.title("Login Page")
root.configure(bg="white")

# Detect screen size and calculate scaling
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

scale_x = screen_width / 1920
scale_y = screen_height / 1080
scale_font = (scale_x + scale_y) / 2

# Dynamic font function
def scaled_font(name, size, weight="normal"):
    return (name, int(size * scale_font), weight)

# Login container
container_width = int(500 * scale_x)
container_height = int(500 * scale_y)
container = tk.Frame(
    root,
    bg="#f0f0f0",
    bd=1,
    relief="solid",
    highlightbackground="darkblue",
    highlightthickness=0
)
container.place(relx=0.5, rely=0.5, anchor="center", width=container_width, height=container_height)

# Logo (scaled)
try:
    image = Image.open("logo.png")
    image = image.resize((int(100 * scale_x), int(100 * scale_y)))
    logo = ImageTk.PhotoImage(image)
    logo_label = tk.Label(container, image=logo, bg="#f0f0f0")
    logo_label.image = logo
    logo_label.pack(pady=(int(20 * scale_y), int(10 * scale_y)))
except:
    logo_label = tk.Label(container, text="Your Logo",
                          font=scaled_font("Arial", 16, "bold"),
                          bg="#f0f0f0")
    logo_label.pack(pady=(int(20 * scale_y), int(10 * scale_y)))

# Label and entry fonts
label_font = scaled_font("Helvetica", 12)
entry_font = scaled_font("Helvetica", 12)

# Input fields
def create_input(label_text, entry_var):
    tk.Label(container, text=label_text, font=label_font, bg="#f0f0f0").pack(pady=(int(10 * scale_y), 0))
    entry = tk.Entry(container, font=entry_font, width=int(30 * scale_x), relief="groove", bd=2)
    entry.pack(ipady=int(8 * scale_y), pady=int(5 * scale_y))
    return entry

username_entry = create_input("Username", "username")
company_id_entry = create_input("Company ID", "company_id")
password_entry = tk.Entry(container, font=entry_font, width=int(30 * scale_x), relief="groove", bd=2, show="*")
tk.Label(container, text="Password", font=label_font, bg="#f0f0f0").pack(pady=(int(10 * scale_y), 0))
password_entry.pack(ipady=int(8 * scale_y), pady=int(5 * scale_y))

# Login button
def on_login_hover(e):
    login_btn.config(bg="#3498DB")

def on_login_leave(e):
    login_btn.config(bg="#3E84FB")

login_btn = tk.Button(
    container,
    text="Login",
    font=scaled_font("Helvetica", 13, "bold"),
    bg="#3E84FB",
    fg="white",
    activebackground="#3498DB",
    activeforeground="white",
    width=int(20 * scale_x),
    relief="flat",
    bd=0,
    command=login
)
login_btn.pack(pady=int(20 * scale_y), ipadx=int(5 * scale_x), ipady=int(5 * scale_y))
login_btn.bind("<Enter>", on_login_hover)
login_btn.bind("<Leave>", on_login_leave)

# Forgot Password
forgot_label = tk.Label(container,
                        text="Forgot Password?",
                        font=scaled_font("Helvetica", 10),
                        fg="blue", cursor="hand2", bg="#f0f0f0")
forgot_label.pack()
forgot_label.bind("<Button-1>", lambda e: forgot_password())

root.mainloop()
