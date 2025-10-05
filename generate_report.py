import os
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# PDF (no charts, clean summary like your old version)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "sample_data.db")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
LOGO_CANDIDATES = ["scraplogo.png", "scraplogo.jpg", "scraplogo.jpeg", "logo.png"]

def get_conn():
    return sqlite3.connect(DB_PATH)

def _find_logo_path():
    for name in LOGO_CANDIDATES:
        p = os.path.join(IMAGE_DIR, name)
        if os.path.exists(p):
            return p
    return None


class GenerateReportFrame(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg="#F8FAFC")
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="Generate Report",
                 font=("Segoe UI", 28, "bold"),
                 bg="#F8FAFC", fg="#0F172A").pack(pady=(24, 8))

        # Filter row (same look/feel as before)
        filt = tk.Frame(self, bg="#F8FAFC")
        filt.pack(pady=6)

        tk.Label(filt, text="From (MM/DD/YYYY):", font=("Segoe UI", 11, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=0, padx=6, sticky="e")
        self.from_entry = tk.Entry(filt, font=("Segoe UI", 11), width=14)
        self.from_entry.grid(row=0, column=1, padx=6)

        tk.Label(filt, text="To (MM/DD/YYYY):", font=("Segoe UI", 11, "bold"),
                 bg="#F8FAFC", fg="#0F172A").grid(row=0, column=2, padx=6, sticky="e")
        self.to_entry = tk.Entry(filt, font=("Segoe UI", 11), width=14)
        self.to_entry.grid(row=0, column=3, padx=6)

        actions = tk.Frame(self, bg="#F8FAFC")
        actions.pack(pady=(10, 16))
        ttk.Button(actions, text="Generate Report (PDF)", command=self.on_generate).pack(side="left", padx=6)
        ttk.Button(actions, text="Export CSV (table data)", command=self.on_export_csv).pack(side="left", padx=6)

        # Minimal preview table like your old layout
        self.tree = ttk.Treeview(self, columns=("date", "machine_operator", "machine_name", "quantity", "unit", "shift", "reason"),
                                 show="headings", height=14)
        headers = {
            "date": "Date", "machine_operator": "Operator", "machine_name": "Machine",
            "quantity": "Quantity", "unit": "Unit", "shift": "Shift", "reason": "Reason"
        }
        for c in self.tree["columns"]:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, anchor="center", width=130)
        self.tree.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        self._current_rows = []  # cached rows last query

    def _parse_range(self):
        f = self.from_entry.get().strip()
        t = self.to_entry.get().strip()
        # optional range; validate when provided
        fmt = "%m/%d/%Y"
        if f:
            try: datetime.strptime(f, fmt)
            except ValueError: raise ValueError("Invalid From date. Use MM/DD/YYYY.")
        if t:
            try: datetime.strptime(t, fmt)
            except ValueError: raise ValueError("Invalid To date. Use MM/DD/YYYY.")
        return f, t

    def _run_query(self, start_s, end_s):
        q = """SELECT date, machine_operator, machine_name, quantity, unit, shift, reason
               FROM scrap_logs"""
        params = []
        if start_s and end_s:
            q += " WHERE date BETWEEN ? AND ?"
            params.extend([start_s, end_s])
        q += " ORDER BY date ASC, id ASC"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(q, params)
            return cur.fetchall()

    def _refresh_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=r)

    # --- Buttons ---
    def on_generate(self):
        try:
            start_s, end_s = self._parse_range()
        except ValueError as e:
            messagebox.showerror("Invalid Date", str(e))
            return

        try:
            rows = self._run_query(start_s, end_s)
            if not rows:
                messagebox.showinfo("No Data", "No scrap logs for the selected range.")
                self._current_rows = []
                self._refresh_table([])
                return
            self._current_rows = rows
            self._refresh_table(rows)
            pdf_path = self._export_pdf(rows, start_s, end_s)
            messagebox.showinfo("Success", f"Report successfully generated and saved!\n\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate report.\n\n{e}")

    def on_export_csv(self):
        if not self._current_rows:
            messagebox.showinfo("Export", "Generate or load data first.")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV Files", "*.csv")],
                                          initialfile=f"ScrapSense_Export_{datetime.now().strftime('%Y-%m-%d')}.csv")
        if not fp: return
        import csv
        with open(fp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date","Operator","Machine","Quantity","Unit","Shift","Reason"])
            for r in self._current_rows:
                writer.writerow(list(r))
        messagebox.showinfo("Export", f"CSV saved to:\n{fp}")

    # --- PDF export (old style: clean summary, tables, no charts) ---
    def _export_pdf(self, rows, start_s, end_s):
        today = datetime.now().strftime("%Y-%m-%d")
        pdf_name = f"ScrapSense_Report_{today}.pdf"
        pdf_path = os.path.join(BASE_DIR, pdf_name)

        doc = SimpleDocTemplate(pdf_path, pagesize=LETTER,
                                leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()
        H = styles["Heading1"]
        H.fontName = "Helvetica-Bold"
        H.textColor = colors.HexColor("#1F3B4D")
        P = styles["BodyText"]

        # Header with logo if available
        logo = _find_logo_path()
        if logo:
            story.append(RLImage(logo, width=140, height=140 * 0.28))  # scale height roughly
            story.append(Spacer(1, 6))

        # Title / daterange
        title = "ScrapSense Report"
        story.append(Paragraph(title, H))
        if start_s and end_s:
            story.append(Paragraph(f"Date Range: {start_s} to {end_s}", P))
        else:
            story.append(Paragraph("Date Range: All Data", P))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", P))
        story.append(Spacer(1, 10))

        # --- Summary stats ---
        total_qty = sum(float(r[3]) for r in rows)
        total_rows = len(rows)
        # by machine / reason / shift
        from collections import Counter
        by_machine = Counter(r[2] for r in rows)
        by_reason = Counter(r[6] for r in rows)
        by_shift  = Counter(r[5] for r in rows)

        summary_tbl = Table([
            ["Total Entries", str(total_rows)],
            ["Total Scrap", f"{int(total_qty)} (mixed units)"],
            ["Top Machine", (by_machine.most_common(1)[0][0] if by_machine else "—")],
            ["Top Reason", (by_reason.most_common(1)[0][0] if by_reason else "—")],
            ["Top Shift",  (by_shift.most_common(1)[0][0] if by_shift else "—")],
        ], colWidths=[150, 340])
        summary_tbl.setStyle(TableStyle([
            ("FONT", (0,0), (-1,-1), "Helvetica", 10),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 12))

        # --- Scrap by Machine ---
        story.append(Paragraph("Scrap by Machine", styles["Heading2"]))
        machine_rows = [["Machine", "Count (rows)"]]
        for name, cnt in by_machine.most_common():
            machine_rows.append([name, str(cnt)])
        story.append(self._styled_table(machine_rows))
        story.append(Spacer(1, 10))

        # --- Scrap by Reason ---
        story.append(Paragraph("Scrap by Reason", styles["Heading2"]))
        reason_rows = [["Reason", "Count (rows)"]]
        for name, cnt in by_reason.most_common():
            reason_rows.append([name, str(cnt)])
        story.append(self._styled_table(reason_rows))
        story.append(Spacer(1, 10))

        # --- Detail table (compact) ---
        story.append(Paragraph("Details", styles["Heading2"]))
        detail_header = ["Date", "Operator", "Machine", "Quantity", "Unit", "Shift", "Reason"]
        detail_rows = [detail_header] + [list(r) for r in rows]
        story.append(self._styled_table(detail_rows, small=True))
        story.append(Spacer(1, 10))

        # Demo note
        story.append(Paragraph(
            "<i>Note: This sample data is auto-generated for demonstration purposes.</i>",
            styles["Italic"]
        ))

        doc.build(story)
        return pdf_path

    def _styled_table(self, rows, small=False):
        col_widths = None
        if small:
            col_widths = [70, 80, 90, 60, 40, 60, 130]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("FONT", (0,0), (-1,-1), "Helvetica", 9 if small else 10),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#111827")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("ALIGN", (3,1), (3,-1), "RIGHT"),  # quantity right-aligned
        ]))
        return t


# Standalone run
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Generate Report — ScrapSense")
    app = GenerateReportFrame(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
