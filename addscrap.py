import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import Calendar
from datetime import datetime
import os
import psycopg2
import pandas as pd

class AddScrapFrame(tk.Frame):
    def __init__(self, parent, controller, image_dir="./images"):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self.image_dir = image_dir

        # Global caret style so insertion cursor is visible everywhere
        self.option_add('*Entry.insertBackground', 'black')
        self.option_add('*Text.insertBackground', 'black')
        self.option_add('*TCombobox*insertBackground', 'black')

        self.scale_x = self.winfo_screenwidth() / 1920
        self.scale_y = self.winfo_screenheight() / 1080
        self.scale_font = (self.scale_x + self.scale_y) / 2

        self.fields = {}
        self.shift_suggestions = []
        self.build_interface()

    def enable_focus(self, widget):
        """Force widget to grab keyboard focus on click."""
        widget.bind("<Button-1>", lambda e: e.widget.focus_set())

    def get_db_connection(self):
        return psycopg2.connect(
            dbname="scrapsense",
            user="postgres",
            password="",  # Set if needed
            host="localhost",
            port="5432"
        )

    def fetch_shift_suggestions(self):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT shift FROM scrap_logs ORDER BY shift ASC")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self.shift_suggestions = [r[0] for r in rows if r[0]]
        except Exception:
            self.shift_suggestions = []
        if "shift" in self.fields:
            current = self.fields["shift"].get().lower()
            if current:
                self.fields["shift"]["values"] = [s for s in self.shift_suggestions if current in s.lower()]
            else:
                self.fields["shift"]["values"] = self.shift_suggestions

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%m/%d/%Y")
            return True
        except ValueError:
            return False

    def entry_exists(self, date):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM scrap_logs WHERE date = %s", (date,))
            exists = cur.fetchone() is not None
            cur.close()
            conn.close()
            return exists
        except Exception:
            return False

    def overwrite_entry(self, date):
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM scrap_logs WHERE date = %s", (date,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass

    def build_interface(self):
        self.time_label = tk.Label(self, font=("Segoe UI", int(14*self.scale_font)),
                                   bg="#F8FAFC", fg="#475569")
        self.time_label.place(relx=0.98, y=int(42*self.scale_y), anchor="ne")
        self.update_time()

        tk.Label(self, text="Add Scrap",
                 font=("Segoe UI", int(44*self.scale_font), "bold"),
                 bg="#F8FAFC", fg="#0F172A").pack(
            pady=(int(80*self.scale_y), int(28*self.scale_y)))

        form_frame = tk.Frame(self, bg="white",
                              padx=int(40*self.scale_x), pady=int(40*self.scale_y),
                              highlightbackground="#E2E8F0", highlightthickness=1)
        form_frame.pack()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground="white", background="white",
                        foreground="black", padding=int(5*self.scale_y))

        # Entry Type
        self._create_label(form_frame, "Entry Type:", 0)
        entry_type = ttk.Combobox(form_frame,
                                  values=["Manual Entry", "Import Document"], width=47,
                                  font=("Segoe UI", int(12*self.scale_font)),
                                  state="normal")
        self.enable_focus(entry_type)
        entry_type.set("Select Entry Type")
        entry_type.grid(row=0, column=1, sticky="w", pady=int(10*self.scale_y))
        entry_type.bind("<<ComboboxSelected>>", self.handle_entry_type_change)
        self.fields["entry_type"] = entry_type

        # Machine Operator
        self._create_label(form_frame, "Machine Operator (ID):", 1)
        mop_entry = tk.Entry(form_frame, width=50,
                             font=("Segoe UI", int(12*self.scale_font)),
                             fg="black", bg="#F9FAFB", relief="flat",
                             highlightthickness=2,
                             highlightbackground="#E2E8F0",
                             highlightcolor="#2563EB",
                             insertbackground="black")
        self.enable_focus(mop_entry)
        mop_entry.grid(row=1, column=1, sticky="w", pady=int(10*self.scale_y), ipady=int(5*self.scale_y))
        self.fields["machine_operator"] = mop_entry

        # Date
        self._create_label(form_frame, "Date (MM/DD/YYYY):", 2)
        date_frame = tk.Frame(form_frame, bg="white")
        date_frame.grid(row=2, column=1, sticky="w", pady=int(10*self.scale_y))
        date_entry = tk.Entry(date_frame, width=47,
                              font=("Segoe UI", int(12*self.scale_font)),
                              fg="black", bg="#F9FAFB", relief="flat",
                              highlightthickness=2,
                              highlightbackground="#E2E8F0",
                              highlightcolor="#2563EB",
                              insertbackground="black")
        self.enable_focus(date_entry)
        date_entry.insert(0, datetime.now().strftime("%m/%d/%Y"))
        date_entry.pack(side="left", ipady=int(5*self.scale_y))
        self.fields["date"] = date_entry

        calendar_icon_path = os.path.join(self.image_dir, "schedule.png")
        if os.path.isfile(calendar_icon_path):
            from PIL import Image, ImageTk
            img = Image.open(calendar_icon_path).convert("RGBA")
            img = img.resize((20, 20))
            self.calendar_img = ImageTk.PhotoImage(img)
            cal_btn = tk.Button(date_frame, image=self.calendar_img, command=self.open_calendar,
                                bg="white", bd=0, cursor="hand2")
        else:
            cal_btn = tk.Button(date_frame, text="📅", command=self.open_calendar, bg="white", bd=0, cursor="hand2")
        cal_btn.pack(side="left", padx=5)
        self.cal_btn = cal_btn

        # Quantity + unit
        self._create_label(form_frame, "Quantity:", 3)
        qty_frame = tk.Frame(form_frame, bg="white")
        qty_frame.grid(row=3, column=1, sticky="w", pady=int(10*self.scale_y))
        quantity_entry = tk.Entry(qty_frame, width=30,
                                  font=("Segoe UI", int(12*self.scale_font)),
                                  fg="black", bg="#F9FAFB", relief="flat",
                                  highlightthickness=2,
                                  highlightbackground="#E2E8F0",
                                  highlightcolor="#2563EB",
                                  insertbackground="black")
        self.enable_focus(quantity_entry)
        quantity_entry.pack(side="left", ipady=int(5*self.scale_y))
        unit_dropdown = ttk.Combobox(qty_frame, values=["lb", "kg", "units", "grams"], width=5,
                                     font=("Segoe UI", int(12*self.scale_font)), state="normal")
        self.enable_focus(unit_dropdown)
        unit_dropdown.set("Select")
        unit_dropdown.pack(side="left", padx=int(12*self.scale_x))
        self.fields["quantity"] = quantity_entry
        self.fields["unit"] = unit_dropdown

        # Shift
        self._create_label(form_frame, "Shift:", 4)
        self.fetch_shift_suggestions()
        shift_var = tk.StringVar()
        shift_entry = ttk.Combobox(form_frame, textvariable=shift_var,
                                   values=self.shift_suggestions,
                                   width=47, font=("Segoe UI", int(12*self.scale_font)),
                                   state="normal")
        self.enable_focus(shift_entry)
        shift_entry.set("Type or Select Shift")
        shift_entry.grid(row=4, column=1, sticky="w", pady=int(10*self.scale_y))
        self.fields["shift"] = shift_entry

        # Reason
        self._create_label(form_frame, "Reason:", 5)
        reason_entry = tk.Entry(form_frame, width=50,
                                font=("Segoe UI", int(12*self.scale_font)),
                                fg="black", bg="#F9FAFB", relief="flat",
                                highlightthickness=2,
                                highlightbackground="#E2E8F0",
                                highlightcolor="#2563EB",
                                insertbackground="black")
        self.enable_focus(reason_entry)
        reason_entry.grid(row=5, column=1, sticky="w", pady=int(10*self.scale_y), ipady=int(5*self.scale_y))
        self.fields["reason"] = reason_entry

        # Comments
        self._create_label(form_frame, "Additional Comments:", 6)
        comments_text = tk.Text(form_frame, width=50, height=5,
                                font=("Segoe UI", int(12*self.scale_font)),
                                fg="black", bg="#F9FAFB", relief="flat",
                                highlightthickness=2,
                                highlightbackground="#E2E8F0",
                                highlightcolor="#2563EB",
                                insertbackground="black")
        self.enable_focus(comments_text)
        comments_text.grid(row=6, column=1, sticky="w", pady=int(10*self.scale_y))
        self.fields["comments"] = comments_text

        # Submit Button
        style.configure("Green.TButton",
                        background="#22C55E", foreground="white",
                        font=("Segoe UI", int(16 * self.scale_font), "bold"),
                        padding=int(10 * self.scale_y))
        style.map("Green.TButton", background=[("active", "#16A34A")])
        ttk.Button(self, text="Submit Scrap Entry", style="Green.TButton",
                   cursor="hand2", command=self.submit_scrap_entry).pack(
            pady=int(30 * self.scale_y), ipady=int(5 * self.scale_y))

    def _create_label(self, parent, text, row):
        tk.Label(parent, text=text, font=("Segoe UI", int(14*self.scale_font), "bold"),
                 bg="white", fg="#334155", anchor="w").grid(
            row=row, column=0, sticky="w", pady=int(10*self.scale_y), padx=int(10*self.scale_x))

    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
        self.after(1000, self.update_time)

    def open_calendar(self):
        top = tk.Toplevel(self)
        top.title("Select Date")
        cal = Calendar(top, selectmode="day", year=datetime.now().year,
                       month=datetime.now().month, day=datetime.now().day)
        cal.pack(pady=20)
        def pick_date():
            self.fields["date"].delete(0, tk.END)
            self.fields["date"].insert(0, cal.get_date())
            top.destroy()
        ttk.Button(top, text="Select", command=pick_date).pack(pady=10)

    def handle_entry_type_change(self, event):
        if self.fields["entry_type"].get() == "Import Document":
            self.import_document()

    def submit_scrap_entry(self):
        machine_operator = self.fields["machine_operator"].get().strip()
        date = self.fields["date"].get().strip()
        quantity = self.fields["quantity"].get().strip()
        unit = self.fields["unit"].get().strip()
        shift = self.fields["shift"].get().strip()
        reason = self.fields["reason"].get().strip()
        comments = self.fields["comments"].get("1.0", tk.END).strip()
        if not machine_operator or not date or not quantity or not shift or "Select" in shift or not unit or unit == "Select":
            messagebox.showerror("Validation Error", "Please fill in all required fields.")
            return
        if not self.validate_date(date):
            messagebox.showerror("Validation Error", "Date must be in MM/DD/YYYY format.")
            return
        try:
            quantity_num = float(quantity)
            if quantity_num <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Validation Error", "Quantity must be a positive number.")
            return
        shift_normalized = shift.upper().strip()
        if self.entry_exists(date):
            if not messagebox.askyesno("Duplicate Date Entry",
                                       f"There is already an entry for {date}. Do you wish to overwrite it?"):
                return
            self.overwrite_entry(date)
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scrap_logs (machine_operator, date, quantity, unit, shift, reason, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (machine_operator, date, quantity_num, unit, shift_normalized, reason, comments))
            conn.commit()
            cur.close()
            conn.close()
            messagebox.showinfo("Success", "Scrap entry saved successfully!")
            self.fetch_shift_suggestions()
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def import_document(self):
        file_path = filedialog.askopenfilename(title="Select Document",
                                               filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx *.xls")])
        if not file_path: return
        try:
            df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
            if df.empty:
                messagebox.showwarning("Empty File", "The selected file has no data.")
                return
            inserted, overwritten = 0, 0
            for _, row in df.iterrows():
                mop = row.get("machine operator id", "")
                date = row.get("date", datetime.now().strftime("%m/%d/%Y"))
                qty = row.get("quantity", "")
                unit = row.get("unit", "lb")
                shift = str(row.get("shift", "")).strip().upper()
                reason = row.get("reason", "")
                comments = row.get("comments", "")
                if not mop or not date or not qty or not shift or shift == "Select Shift" or not unit or unit == "Select":
                    continue
                try:
                    qty_num = float(qty)
                    if qty_num <= 0:
                        continue
                except ValueError:
                    continue
                if self.entry_exists(date):
                    if not messagebox.askyesno("Duplicate Date Entry", f"There is already an entry for {date}. Do you wish to overwrite it?"):
                        continue
                    self.overwrite_entry(date)
                    overwritten += 1
                try:
                    conn = self.get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO scrap_logs (machine_operator, date, quantity, unit, shift, reason, comments)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (mop, date, qty_num, unit, shift, reason, comments))
                    conn.commit()
                    cur.close()
                    conn.close()
                    inserted += 1
                except Exception:
                    continue
            self.fetch_shift_suggestions()
            messagebox.showinfo("Import Result",
                                f"Imported {inserted} records successfully.\nOverwritten: {overwritten} records.")
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")
