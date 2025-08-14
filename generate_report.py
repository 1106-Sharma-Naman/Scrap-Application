# generate_report.py
import os
import tempfile
from datetime import datetime, date

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from tkcalendar import Calendar
import psycopg2
import pandas as pd

# Matplotlib strictly for offscreen chart images used in the PDF
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# -------- ReportLab imports --------
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle
)

# ===============================
# BRAND / THEME
# ===============================
APP_BG        = "#ECF4FA"
CARD_BG       = "#FFFFFF"
BORDER_COLOR  = "#E5E7EB"
TEXT_MAIN     = "#0E2A47"
TEXT_SECOND   = "#374151"
TEXT_MUTED    = "#6B7280"

PRIMARY_BG    = "#16A34A"
PRIMARY_FG    = "#FFFFFF"
PRIMARY_BG_HI = "#12833B"

NEUTRAL_BG    = "#E5E7EB"
NEUTRAL_FG    = "#111827"

ROW_A         = "#FFFFFF"
ROW_B         = "#F9FAFB"
HEAD_BG       = "#F3F4F6"
HEAD_FG       = "#111827"

FONT_FAMILY   = "Segoe UI"

# Images
IMAGE_DIR             = os.path.join(os.path.dirname(__file__), "images")
ICON_REPORT_HEADER    = "icon_report.png"
ICON_PREVIEW          = "icon_view.png"
ICON_EXPORT           = "icon_pdf.png"
ICON_KPI_TOTAL        = "kpi_weight.png"
ICON_KPI_ENTRIES      = "kpi_list.png"
ICON_KPI_AVGDAY       = "kpi_trend.png"
ICON_KPI_TOPREASON    = "kpi_cause.png"
ICON_CALENDAR         = "schedule.png"
LOGO_PATH             = "scrapsense_logo.png"

DEFAULT_SAVE_NAME     = "ScrapSense_Report.pdf"

# ===============================
# DB CONNECTION (env-based)
# ===============================
def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if (val is not None and val != "") else default

def get_db_connection():
    """
    Reads PG* env vars. Defaults:
      host=127.0.0.1 port=5432 db=scrapsense user=scrapsense
    We also set search_path=public so unqualified names resolve there.
    """
    host = _env("PGHOST", "127.0.0.1")
    port = int(_env("PGPORT", "5432"))
    db   = _env("PGDATABASE", "scrapsense")
    user = _env("PGUSER", "scrapsense")
    pwd  = _env("PGPASSWORD", "")

    # options can push session GUCs at connect time
    return psycopg2.connect(
        dbname=db,
        user=user,
        password=pwd,
        host=host,
        port=port,
        connect_timeout=10,
        options="-c search_path=public"
    )

def table_has_column(conn, table_name: str, column_name: str, schema: str = "public") -> bool:
    """Return True if the column exists in the table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s
            LIMIT 1
        """, (schema, table_name, column_name))
        return cur.fetchone() is not None

# ===============================
# UTIL: load icon safely
# ===============================
def load_icon(filename, size):
    from PIL import Image, ImageTk
    try:
        path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ===============================
# DATA ACCESS
# ===============================
def load_scrap_data(start_date, end_date, shift=None, operator=None, reason=None):
    """
    Loads scrap data into a DataFrame from public.scrap_logs.
    Includes optional columns automatically if present:
      - entry_type
      - total_produced
    """
    conn = get_db_connection()
    try:
        has_entry_type = table_has_column(conn, "scrap_logs", "entry_type", "public")
        has_total_prod = table_has_column(conn, "scrap_logs", "total_produced", "public")

        select_cols = [
            "id",
            "machine_operator",
            "date::date AS date",
            "quantity::numeric AS quantity",
            "unit",
            "shift",
            "reason",
            "comments",
        ]
        if has_total_prod:
            select_cols.append("total_produced::numeric AS total_produced")
        if has_entry_type:
            select_cols.append("entry_type")

        conditions = ["date::date BETWEEN %(start)s AND %(end)s"]
        params = {"start": start_date, "end": end_date}

        if shift and shift != "All":
            conditions.append("shift = %(shift)s")
            params["shift"] = shift
        if operator:
            conditions.append("machine_operator ILIKE %(operator)s")
            params["operator"] = f"%{operator.strip()}%"
        if reason:
            conditions.append("reason ILIKE %(reason)s")
            params["reason"] = f"%{reason.strip()}%"

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT {", ".join(select_cols)}
            FROM public.scrap_logs
            WHERE {where_clause}
            ORDER BY date ASC, id ASC
        """

        df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            return df

        # normalize types
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)

        if "total_produced" in df.columns:
            df["total_produced"] = pd.to_numeric(df.get("total_produced"), errors="coerce")

        # add scrap_percent if we have total_produced
        if "total_produced" in df.columns:
            df["scrap_percent"] = df.apply(
                lambda r: (float(r["quantity"]) / float(r["total_produced"]) * 100.0)
                if pd.notnull(r["total_produced"]) and float(r["total_produced"]) > 0 else None,
                axis=1
            )

        return df
    finally:
        conn.close()

# ===============================
# ANALYTICS / CHARTS
# ===============================
def compute_kpis(df: pd.DataFrame):
    if df.empty:
        return {"total_scrap": 0, "entries": 0, "avg_per_day": 0, "top_reason": "—", "scrap_rate": None}
    total = float(df["quantity"].sum())
    entries = int(len(df))
    per_day = df.groupby("date")["quantity"].sum()
    avg_day = float(per_day.mean()) if not per_day.empty else 0.0
    top_reason = df.groupby("reason")["quantity"].sum().sort_values(ascending=False)
    top_reason_label = top_reason.index[0] if len(top_reason) else "—"

    # overall scrap rate if total_produced exists
    scrap_rate = None
    if "total_produced" in df.columns:
        denom = df["total_produced"].dropna().sum()
        if denom and denom > 0:
            scrap_rate = total / denom * 100.0

    return {
        "total_scrap": total,
        "entries": entries,
        "avg_per_day": avg_day,
        "top_reason": top_reason_label if top_reason_label else "—",
        "scrap_rate": scrap_rate,
    }

def make_line_chart(df: pd.DataFrame, out_path: str):
    # Daily total
    daily = df.groupby("date")["quantity"].sum()
    plt.figure(figsize=(7.5, 3.2), dpi=160)
    plt.plot(daily.index, daily.values, marker="o")
    plt.title("Scrap by Day")
    plt.xlabel("Date")
    plt.ylabel("Total Scrap")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout(pad=1.0)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def make_reason_pie(df: pd.DataFrame, out_path: str):
    reason_totals = df.groupby("reason")["quantity"].sum().sort_values(ascending=False)
    if reason_totals.empty:
        plt.figure(figsize=(3.5, 3.5), dpi=160)
        plt.text(0.5, 0.5, "No reason data", ha="center", va="center")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(out_path, bbox_inches="tight")
        plt.close()
        return

    top = reason_totals.head(6)
    if len(reason_totals) > 6:
        top = pd.concat([top, pd.Series({"Others": reason_totals.iloc[6:].sum()})])

    plt.figure(figsize=(3.5, 3.5), dpi=160)
    plt.pie(top.values, labels=top.index, autopct="%1.1f%%", startangle=90)
    plt.title("Scrap Breakdown by Reason")
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

# ===============================
# PDF GENERATION (REPORTLAB)
# ===============================
def build_pdf(df: pd.DataFrame, kpis: dict, start_date: date, end_date: date, save_path: str):
    page_w, page_h = letter
    doc = SimpleDocTemplate(
        save_path,
        pagesize=letter,
        leftMargin=0.6*inch,
        rightMargin=0.6*inch,
        topMargin=0.6*inch,
        bottomMargin=0.6*inch
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="KPILabel", fontName="Helvetica", fontSize=11, leading=13, textColor=colors.HexColor("#4B5563")))
    styles.add(ParagraphStyle(name="KPIValue", fontName="Helvetica-Bold", fontSize=16, leading=18, spaceAfter=6, textColor=colors.black))
    styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8, leading=9))
    styles.add(ParagraphStyle(name="CellBold", fontName="Helvetica-Bold", fontSize=8, leading=9))
    story = []

    # Header with logo or brand text
    header_row = []
    logo_abs = os.path.join(IMAGE_DIR, LOGO_PATH)
    if os.path.exists(logo_abs):
        header_row.append(RLImage(logo_abs, width=1.3*inch, height=1.0*inch))
    else:
        header_row.append(Paragraph("<b>ScrapSense</b>", styles["Title"]))

    title_text = (
        f"<b>Scrap Report</b><br/>"
        f"<font size=10>{start_date:%b %d, %Y} to {end_date:%b %d, %Y}</font><br/>"
        f"<font size=8>Generated {datetime.now():%b %d, %Y %I:%M %p}</font>"
    )
    header_row.append(Paragraph(title_text, styles["Normal"]))

    header_tbl = Table([header_row], colWidths=[1.6*inch, None])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.18*inch))

    # KPIs grid (now with Scrap Rate if available)
    kpi_headers = ["Total Scrap", "Entries", "Avg/Day", "Top Reason", "Scrap Rate"]
    kpi_values = [
        Paragraph(f"{kpis['total_scrap']:.2f}", styles["KPIValue"]),
        Paragraph(f"{kpis['entries']}", styles["KPIValue"]),
        Paragraph(f"{kpis['avg_per_day']:.2f}", styles["KPIValue"]),
        Paragraph(f"{kpis['top_reason']}", styles["KPIValue"]),
        Paragraph(f"{kpis['scrap_rate']:.2f}%" if kpis["scrap_rate"] is not None else "—", styles["KPIValue"]),
    ]

    kpi_table_data = [
        [Paragraph(f"<b>{h}</b>", styles["KPILabel"]) for h in kpi_headers],
        kpi_values
    ]
    kpi_tbl = Table(kpi_table_data, colWidths=[(page_w - doc.leftMargin - doc.rightMargin)/5.0]*5)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("LINEABOVE", (0, 0), (-1, 0), 0.25, colors.HexColor("#D1D5DB")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.22*inch))

    # Charts – generate to temp files and place side-by-side
    with tempfile.TemporaryDirectory() as td:
        line_path = os.path.join(td, "line.png")
        pie_path = os.path.join(td, "pie.png")
        make_line_chart(df, line_path)
        make_reason_pie(df, pie_path)

        charts_tbl = Table([
            [
                RLImage(line_path, width=4.5*inch, height=2.2*inch),
                RLImage(pie_path,  width=2.7*inch, height=2.7*inch),
            ]
        ], colWidths=[4.7*inch, None])
        charts_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(charts_tbl)

        story.append(Spacer(1, 0.28*inch))
        story.append(Paragraph("<b>Data (sample)</b>", styles["Heading3"]))
        story.append(Spacer(1, 0.10*inch))

        # ----- Data table (auto-fit to page width, wrap long cells) -----
        base_cols = ["date", "shift", "machine_operator", "reason", "quantity", "unit"]
        if "total_produced" in df.columns:
            base_cols += ["total_produced", "scrap_percent"]
        if "entry_type" in df.columns:
            base_cols += ["entry_type"]
        base_cols += ["comments"]

        table_header = [Paragraph(f"<b>{c.replace('_', ' ').title()}</b>", styles["CellBold"]) for c in base_cols]
        data_tbl = [table_header]

        def fmt_num(val, nd=2):
            try:
                return f"{float(val):.{nd}f}"
            except Exception:
                return "" if pd.isna(val) else str(val)

        for _, r in df[base_cols].iterrows():
            row = []
            for c in base_cols:
                v = r[c]
                if c == "date":
                    v = str(v)
                elif c in ("quantity", "total_produced", "scrap_percent"):
                    v = (fmt_num(v, 2) + ("%" if c == "scrap_percent" and pd.notnull(r.get("scrap_percent")) else "")) if pd.notnull(v) else ""
                else:
                    v = "" if pd.isna(v) else str(v)

                row.append(Paragraph(v, styles["Cell"]))
            data_tbl.append(row)

        avail_w = page_w - doc.leftMargin - doc.rightMargin
        width_map = {
            "date": 0.10, "shift": 0.09, "machine_operator": 0.15,
            "reason": 0.14, "quantity": 0.09, "unit": 0.07,
            "total_produced": 0.11, "scrap_percent": 0.10,
            "entry_type": 0.09, "comments": 0.16
        }
        fracs = [width_map[c] for c in base_cols]
        s = sum(fracs)
        fracs = [f/s for f in fracs]
        col_widths = [f * avail_w for f in fracs]

        tbl = Table(data_tbl, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)

        doc.build(story)

# ===============================
# TKINTER FRAME
# ===============================
class GenerateReportFrame(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        self.current_df = pd.DataFrame()
        self._calendar_imgs = []  # keep refs to calendar icons
        self._init_style()
        self._build()

    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TLabel", background=APP_BG, foreground=TEXT_SECOND, font=(FONT_FAMILY, 12))
        style.configure("PageTitle.TLabel", background=APP_BG, foreground=TEXT_MAIN, font=(FONT_FAMILY, 24, "bold"))

        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_SECOND, font=(FONT_FAMILY, 12, "bold"))
        style.configure("CardValue.TLabel", background=CARD_BG, foreground=TEXT_MAIN, font=(FONT_FAMILY, 16, "bold"))

        style.configure("Primary.TButton",
                        background=PRIMARY_BG, foreground=PRIMARY_FG,
                        font=(FONT_FAMILY, 12, "bold"), padding=8, relief="flat")
        style.map("Primary.TButton",
                  background=[("active", PRIMARY_BG_HI), ("pressed", PRIMARY_BG_HI)])

        style.configure("Neutral.TButton",
                        background=NEUTRAL_BG, foreground=NEUTRAL_FG,
                        font=(FONT_FAMILY, 12, "bold"), padding=8, relief="flat")

        style.configure("Treeview",
                        background=ROW_A, fieldbackground=ROW_A,
                        foreground="#111", rowheight=28, font=(FONT_FAMILY, 11))
        style.configure("Treeview.Heading",
                        background=HEAD_BG, foreground=HEAD_FG,
                        font=(FONT_FAMILY, 11, "bold"))
        style.map("Treeview", background=[("selected", "#DBEAFE")])

    def _open_calendar_for(self, target_entry):
        top = tk.Toplevel(self)
        top.title("Select Date")
        top.transient(self.winfo_toplevel())
        top.grab_set()
        x = target_entry.winfo_rootx()
        y = target_entry.winfo_rooty() + target_entry.winfo_height() + 6
        top.geometry(f"+{x}+{y}")

        today = datetime.now()
        cal = Calendar(top, selectmode="day", year=today.year, month=today.month, day=today.day)
        cal.pack(padx=12, pady=12)

        def pick_date():
            raw = cal.get_date()
            dt = None
            for fmt in ("%m/%d/%y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    pass
            if dt is None:
                dt = today
            target_entry.delete(0, tk.END)
            target_entry.insert(0, dt.strftime("%Y-%m-%d"))
            top.destroy()

        ttk.Button(top, text="Select", command=pick_date).pack(pady=8)

    def _calendar_button(self, parent, target_entry):
        img = load_icon(ICON_CALENDAR, (20, 20))
        btn = tk.Button(parent,
                        image=img if img else None,
                        text="" if img else "📅",
                        bg=CARD_BG, bd=0, cursor="hand2",
                        command=lambda: self._open_calendar_for(target_entry))
        if img:
            self._calendar_imgs.append(img)
        return btn

    def _build(self):
        # Header
        header_row = tk.Frame(self, bg=APP_BG)
        header_row.pack(fill="x", padx=24, pady=(20, 8))

        icon = load_icon(ICON_REPORT_HEADER, (28, 28))
        if icon:
            tk.Label(header_row, image=icon, bg=APP_BG).pack(side="left")
            self._icon_header = icon

        ttk.Label(header_row, text="Generate Reports", style="PageTitle.TLabel").pack(side="left", padx=(10, 0))

        # Filters Card
        filt = tk.Frame(self, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_COLOR)
        filt.pack(fill="x", padx=24, pady=(0, 12))

        row = tk.Frame(filt, bg=CARD_BG)
        row.pack(fill="x", padx=16, pady=12)

        # Start Date
        ttk.Label(row, text="Start Date:", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.start_date = ttk.Entry(row, width=16)
        self.start_date.grid(row=0, column=1, sticky="w")
        self._calendar_button(row, self.start_date).grid(row=0, column=2, sticky="w", padx=(8, 16))

        # End Date
        ttk.Label(row, text="End Date:", style="Card.TLabel").grid(row=0, column=3, sticky="w", padx=(0, 6))
        self.end_date = ttk.Entry(row, width=16)
        self.end_date.grid(row=0, column=4, sticky="w")
        self._calendar_button(row, self.end_date).grid(row=0, column=5, sticky="w", padx=(8, 16))

        # Shift
        ttk.Label(row, text="Shift:", style="Card.TLabel").grid(row=0, column=6, sticky="w", padx=(0, 6))
        self.shift_var = tk.StringVar(value="All")
        self.shift_combo = ttk.Combobox(row, textvariable=self.shift_var, state="readonly",
                                        values=["All", "A", "B", "C"], width=16)
        self.shift_combo.grid(row=0, column=7, sticky="w", padx=(0, 16))

        # Operator
        ttk.Label(row, text="Operator:", style="Card.TLabel").grid(row=0, column=8, sticky="w", padx=(0, 6))
        self.operator_entry = ttk.Entry(row, width=20)
        self.operator_entry.grid(row=0, column=9, sticky="w", padx=(0, 16))

        # Reason
        ttk.Label(row, text="Reason:", style="Card.TLabel").grid(row=0, column=10, sticky="w", padx=(0, 6))
        self.reason_entry = ttk.Entry(row, width=22)
        self.reason_entry.grid(row=0, column=11, sticky="w")

        # Buttons row
        btns = tk.Frame(filt, bg=CARD_BG)
        btns.pack(fill="x", padx=16, pady=(8, 12))

        preview_icon = load_icon(ICON_PREVIEW, (18, 18))
        export_icon = load_icon(ICON_EXPORT, (18, 18))

        self.preview_btn = ttk.Button(btns, text="  Preview Data", style="Neutral.TButton", command=self.on_preview)
        if preview_icon:
            self.preview_btn.config(image=preview_icon, compound="left")
            self._icon_preview = preview_icon
        self.preview_btn.pack(side="left")

        self.export_btn = ttk.Button(btns, text="  Generate PDF", style="Primary.TButton", command=self.on_export)
        if export_icon:
            self.export_btn.config(image=export_icon, compound="left")
            self._icon_export = export_icon
        self.export_btn.pack(side="left", padx=(10, 0))

        # KPI Row
        kpi_wrap = tk.Frame(self, bg=APP_BG)
        kpi_wrap.pack(fill="x", padx=24)

        self.kpi_vars = {
            "total": tk.StringVar(value="0.00"),
            "entries": tk.StringVar(value="0"),
            "avg": tk.StringVar(value="0.00"),
            "top": tk.StringVar(value="—"),
            "rate": tk.StringVar(value="—"),
        }
        self._build_kpi_card(kpi_wrap, "Total Scrap", self.kpi_vars["total"], ICON_KPI_TOTAL).pack(side="left", padx=(0, 12))
        self._build_kpi_card(kpi_wrap, "Entries", self.kpi_vars["entries"], ICON_KPI_ENTRIES).pack(side="left", padx=(0, 12))
        self._build_kpi_card(kpi_wrap, "Avg/Day", self.kpi_vars["avg"], ICON_KPI_AVGDAY).pack(side="left", padx=(0, 12))
        self._build_kpi_card(kpi_wrap, "Top Reason", self.kpi_vars["top"], ICON_KPI_TOPREASON).pack(side="left", padx=(0, 12))
        self._build_kpi_card(kpi_wrap, "Scrap Rate", self.kpi_vars["rate"]).pack(side="left", padx=(0, 12))

        # Table Card
        table_wrap = tk.Frame(self, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_COLOR)
        table_wrap.pack(fill="both", expand=True, padx=24, pady=12)

        base_cols = ("date", "shift", "machine_operator", "reason", "quantity", "unit",
                     "total_produced", "scrap_percent", "entry_type", "comments")
        self.tree = ttk.Treeview(table_wrap, columns=base_cols, show="headings")
        headings = {
            "date": "Date", "shift": "Shift", "machine_operator": "Machine Operator",
            "reason": "Reason", "quantity": "Quantity", "unit": "Unit",
            "total_produced": "Total Produced", "scrap_percent": "Scrap Percent",
            "entry_type": "Entry Type", "comments": "Comments"
        }
        widths = {
            "date": 110, "shift": 90, "machine_operator": 150, "reason": 140,
            "quantity": 90, "unit": 70, "total_produced": 120, "scrap_percent": 110,
            "entry_type": 100, "comments": 220
        }
        for c in base_cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self.tree.tag_configure("odd", background=ROW_A)
        self.tree.tag_configure("even", background=ROW_B)

        # Defaults: last 7 days
        today = date.today()
        start_default = today if today.day <= 7 else date(today.year, today.month, today.day - 7)
        self.start_date.insert(0, start_default.strftime("%Y-%m-%d"))
        self.end_date.insert(0, today.strftime("%Y-%m-%d"))

    def _build_kpi_card(self, parent, label, var, icon_name=None):
        card = ttk.Frame(parent, style="Card.TFrame")
        card["padding"] = (12, 10, 12, 10)
        card_inner = tk.Frame(card, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_COLOR)
        card_inner.pack(fill="both", expand=True)

        inner = tk.Frame(card_inner, bg=CARD_BG)
        inner.pack(fill="x", expand=True, padx=10, pady=8)

        ic = load_icon(icon_name, (20, 20)) if icon_name else None
        if ic:
            tk.Label(inner, image=ic, bg=CARD_BG).pack(side="left", padx=(0, 8))
            setattr(self, f"_kpi_{label}_icon", ic)

        ttk.Label(inner, text=label, style="Card.TLabel").pack(side="left")
        ttk.Label(card_inner, textvariable=var, style="CardValue.TLabel").pack(anchor="w", padx=10, pady=(4, 4))
        return card

    # -------- helpers --------
    def _parse_date_str(self, s: str) -> date:
        s = s.strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ValueError("Invalid date")

    def _get_filters(self):
        try:
            start = self._parse_date_str(self.start_date.get())
            end = self._parse_date_str(self.end_date.get())
        except Exception:
            messagebox.showerror("Invalid Date", "Dates must be in YYYY-MM-DD or MM/DD/YYYY format.")
            return None

        if start > end:
            messagebox.showerror("Invalid Range", "Start date must be before or equal to end date.")
            return None

        shift = self.shift_var.get()
        operator = self.operator_entry.get().strip()
        reason = self.reason_entry.get().strip()
        return {
            "start": start,
            "end": end,
            "shift": shift,
            "operator": operator if operator else None,
            "reason": reason if reason else None
        }

    # -------- actions --------
    def on_preview(self):
        flt = self._get_filters()
        if not flt:
            return
        df = load_scrap_data(flt["start"], flt["end"], flt["shift"], flt["operator"], flt["reason"])
        self.current_df = df
        self._populate_table(df)

        k = compute_kpis(df)
        self.kpi_vars["total"].set(f"{k['total_scrap']:.2f}")
        self.kpi_vars["entries"].set(str(k["entries"]))
        self.kpi_vars["avg"].set(f"{k['avg_per_day']:.2f}")
        self.kpi_vars["top"].set(k["top_reason"])
        self.kpi_vars["rate"].set(f"{k['scrap_rate']:.2f}%" if k['scrap_rate'] is not None else "—")

        if df.empty:
            messagebox.showinfo("No Data", "No scrap logs found for the selected filters.")

    def _populate_table(self, df: pd.DataFrame):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if df.empty:
            return

        present = set(df.columns)
        for i, r in df.iterrows():
            values = [
                str(r.get("date", "")),
                str(r.get("shift", "")),
                str(r.get("machine_operator", "")),
                str(r.get("reason", "")),
                f"{float(r.get('quantity', 0) or 0):.2f}",
                str(r.get("unit", "")),
                (f"{float(r.get('total_produced')):.2f}" if pd.notnull(r.get("total_produced", None)) else ""),
                (f"{float(r.get('scrap_percent')):.2f}%" if pd.notnull(r.get("scrap_percent", None)) else ""),
                str(r.get("entry_type", "")) if "entry_type" in present else "",
                str(r.get("comments", "")),
            ]
            tag = "even" if (i % 2) else "odd"
            self.tree.insert("", "end", values=values, tags=(tag,))

    def on_export(self):
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("No Data", "Preview data first (or no rows matched your filters).")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=DEFAULT_SAVE_NAME,
            title="Save PDF Report"
        )
        if not path:
            return

        flt = self._get_filters()
        if not flt:
            return

        try:
            kpis = compute_kpis(self.current_df)
            build_pdf(self.current_df, kpis, flt["start"], flt["end"], path)
            messagebox.showinfo("Success", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not generate PDF.\n\n{e}")

# ===============================
# STANDALONE RUN
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("ScrapSense - Generate Report")
    root.configure(bg=APP_BG)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{int(sw*0.8)}x{int(sh*0.8)}+50+50")
    app = GenerateReportFrame(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
