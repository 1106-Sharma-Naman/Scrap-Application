# view_predictions.py — SQLite Recruiter Edition (robust to missing columns)

from dotenv import load_dotenv
load_dotenv()

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Matplotlib must be set to TkAgg before any pyplot import
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from db import get_db_connection  # must return an sqlite3 connection

# -----------------
# SETTINGS / THEME
# -----------------
FILTER_BG = "#DCDAD5"
RISK_COLORS = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#22C55E"}
BG_SIDEBAR = "#DBE2E9"
BG_APP = "white"


# -----------------
# DB (SQLite version, tolerant of schema differences)
# -----------------
def _table_columns(conn, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    # rows are sqlite3.Row if row_factory set; otherwise tuples: (cid, name, type, notnull, dflt_value, pk)
    cols = set()
    for r in rows:
        try:
            cols.add(r["name"])
        except Exception:
            cols.add(r[1])
    return cols


def fetch_logs() -> pd.DataFrame:
    """
    Fetch scrap logs from local SQLite and normalize.
    Tolerates tables missing some columns (unit/shift/reason/machine_*).
    """
    with get_db_connection() as conn:
        # If table doesn't exist, return empty df gracefully
        try:
            conn.execute("SELECT 1 FROM scrap_logs LIMIT 1")
        except Exception:
            return pd.DataFrame()

        cols = _table_columns(conn, "scrap_logs")

        # Pull everything and adapt
        rows = [dict(r) for r in conn.execute("SELECT * FROM scrap_logs").fetchall()]
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # ---- Normalize required columns with safe fallbacks ----
    # date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        # fabricate a date if completely missing (so UI doesn't crash)
        df["date"] = pd.to_datetime("today").normalize()

    df["date"] = df["date"].dt.normalize()

    # quantity (fallback to scrap_weight or 1.0)
    if "quantity" not in df.columns:
        if "scrap_weight" in df.columns:
            df["quantity"] = pd.to_numeric(df["scrap_weight"], errors="coerce")
        else:
            df["quantity"] = 1.0
    else:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    # unit (default lbs)
    if "unit" not in df.columns:
        df["unit"] = "lbs"
    df["unit"] = df["unit"].astype(str)

    # shift (default A)
    if "shift" not in df.columns:
        df["shift"] = "A"
    df["shift"] = (
        df["shift"].astype(str).str.strip().str.upper().str.replace(r"^SHIFT\s+", "", regex=True)
    )

    # reason (optional)
    if "reason" not in df.columns:
        df["reason"] = ""

    # machine key preference
    if "machine_name" in df.columns:
        df["machine_key"] = df["machine_name"].astype(str)
    elif "machine" in df.columns:
        df["machine_key"] = df["machine"].astype(str)
    elif "machine_operator" in df.columns:
        df["machine_key"] = df["machine_operator"].astype(str)
    else:
        df["machine_key"] = "Unknown"

    # comments (optional)
    if "comments" not in df.columns:
        df["comments"] = ""

    # Drop obviously bad rows but keep tolerant on optional fields
    df = df.dropna(subset=["date", "quantity"])
    # If quantity still NaN, coerce to 0 to avoid plot errors
    df["quantity"] = df["quantity"].fillna(0)

    return df


# -----------------
# HELPERS
# -----------------
def apply_date_preset(df: pd.DataFrame, preset: str) -> pd.DataFrame:
    if df.empty:
        return df
    today = datetime.today().date()
    if preset == "Today":
        return df[df["date"].dt.date == today]
    if preset == "This Week":
        monday = today - timedelta(days=datetime.today().weekday())
        return df[df["date"].dt.date >= monday]
    if preset == "This Month":
        first = datetime(today.year, today.month, 1).date()
        return df[df["date"].dt.date >= first]
    if preset == "Last 30 Days":
        return df[df["date"].dt.date >= today - timedelta(days=30)]
    return df


def fit_predict_with_ci(y: np.ndarray, periods_ahead: int = 7, ci=(10, 90)):
    """
    Simple baseline predictor (linear trend + bootstrap residuals).
    Returns arrays with upper/lower confidence bounds.
    """
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y) & ~np.isinf(y)]

    if len(y) == 0:
        empty = np.array([])
        fut = np.zeros(periods_ahead)
        return dict(y_pred=empty, lower=empty, upper=empty,
                    future_pred=fut, future_lower=fut, future_upper=fut,
                    resid=np.array([0.0]))

    if len(y) == 1 or np.allclose(y, y[0]):
        const = np.full(len(y), y.mean())
        fut_const = np.full(periods_ahead, float(y.mean()))
        return dict(y_pred=const, lower=const, upper=const,
                    future_pred=fut_const, future_lower=fut_const, future_upper=fut_const,
                    resid=np.array([0.0]))

    n = len(y)
    x = np.arange(n)
    coef = np.polyfit(x, y, 1)
    trend = np.poly1d(coef)(x)
    resid = y - trend
    if len(resid) < 5:
        resid = np.pad(resid, (0, 5 - len(resid)), constant_values=float(np.mean(resid)))

    sims = 800
    boot_in = np.random.choice(resid, size=(sims, n), replace=True)
    sim_in = trend + boot_in
    lower, upper = np.percentile(sim_in, ci[0], axis=0), np.percentile(sim_in, ci[1], axis=0)

    xf = np.arange(n, n + periods_ahead)
    future_trend = np.poly1d(coef)(xf)
    boot_out = np.random.choice(resid, size=(sims, periods_ahead), replace=True)
    sim_out = future_trend + boot_out
    fl, fu = np.percentile(sim_out, ci[0], axis=0), np.percentile(sim_out, ci[1], axis=0)

    return dict(y_pred=trend, lower=lower, upper=upper,
                future_pred=future_trend, future_lower=fl, future_upper=fu,
                resid=resid)


def risk_bucket(value: float, threshold_low: float, threshold_high: float) -> str:
    if value >= threshold_high:
        return "High"
    if value >= threshold_low:
        return "Medium"
    return "Low"


# -----------------
# DASHBOARD FRAME
# -----------------
class PredictionsDashboardFrame(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg=BG_APP)
        self.controller = controller

        # ----- ttk Style -----
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", padding=6, relief="flat",
                        background="#0078D7", foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", "#005A9E")])
        style.configure("Custom.TCombobox",
                        fieldbackground=FILTER_BG,
                        background=FILTER_BG,
                        selectbackground=FILTER_BG,
                        selectforeground="black")

        # ----- Data & defaults -----
        self.df_raw = fetch_logs()
        self.horizon_days = 7
        # You can tune these thresholds or make them configurable
        self.threshold_low = 2500
        self.threshold_high = 4000

        # ----- Layout -----
        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_top_controls()
        self._build_split_charts()
        self._build_bottom_table()

        self.apply_filters()

    # ----- Sidebar -----
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self, bg=BG_SIDEBAR, padx=10, pady=10)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="ns")
        self.sidebar.columnconfigure(0, weight=1)

        tk.Label(self.sidebar, text="Filters", font=("Segoe UI", 12, "bold"),
                 bg=BG_SIDEBAR).pack(anchor="w", pady=(0, 10))

        tk.Label(self.sidebar, text="Machine:", bg=BG_SIDEBAR).pack(anchor="w")
        machines = ["All"]
        if not self.df_raw.empty:
            machines += sorted(df for df in self.df_raw["machine_key"].dropna().unique().tolist())
        self.machine_cb = ttk.Combobox(self.sidebar, values=machines,
                                       state="readonly", style="Custom.TCombobox")
        self.machine_cb.current(0)
        self.machine_cb.pack(fill="x", pady=5)

        tk.Label(self.sidebar, text="Date:", bg=BG_SIDEBAR).pack(anchor="w", pady=(10, 0))
        self.date_cb = ttk.Combobox(self.sidebar,
                                    values=["Today", "This Week", "This Month", "Last 30 Days"],
                                    state="readonly", style="Custom.TCombobox")
        self.date_cb.current(3)
        self.date_cb.pack(fill="x", pady=5)

        tk.Label(self.sidebar, text="Shift:", bg=BG_SIDEBAR).pack(anchor="w", pady=(10, 0))
        shifts = ["All"]
        if not self.df_raw.empty:
            shifts += sorted(self.df_raw["shift"].dropna().astype(str).str.upper().unique().tolist())
        self.shift_cb = ttk.Combobox(self.sidebar, values=shifts,
                                     state="readonly", style="Custom.TCombobox")
        self.shift_cb.current(0)
        self.shift_cb.pack(fill="x", pady=5)

        ttk.Button(self.sidebar, text="Apply Filters",
                   command=self.apply_filters).pack(fill="x", pady=(20, 0))
        ttk.Button(self.sidebar, text="Reload from DB",
                   command=self._reload_from_db).pack(fill="x", pady=(8, 0))

    # ----- Top controls / charts / table scaffolding -----
    def _build_top_controls(self):
        self.top_controls = tk.Frame(self, bg=BG_APP, padx=10, pady=10)
        self.top_controls.grid(row=0, column=1, sticky="ew")
        self.top_controls.columnconfigure(0, weight=1)

        tk.Label(self.top_controls, text="Scrap Predictions",
                 font=("Segoe UI", 14, "bold"), bg=BG_APP).pack(side="left")
        ttk.Button(self.top_controls, text="Export Data",
                   command=self._export_dummy).pack(side="right", padx=5)
        ttk.Button(self.top_controls, text="Refresh",
                   command=self.apply_filters).pack(side="right", padx=5)

    def _build_split_charts(self):
        self.chart_split = tk.Frame(self, bg=BG_APP, padx=10, pady=10)
        self.chart_split.grid(row=1, column=1, sticky="nsew")
        self.chart_split.rowconfigure(0, weight=1)
        self.chart_split.columnconfigure(0, weight=1)
        self.chart_split.columnconfigure(2, weight=1)
        self.canvas_line = None
        self.canvas_pie = None

    def _build_bottom_table(self):
        self.bottom_frame = tk.Frame(self, bg=BG_APP, padx=10, pady=10)
        self.bottom_frame.grid(row=2, column=1, sticky="nsew")
        self.bottom_frame.rowconfigure(1, weight=1)
        self.bottom_frame.columnconfigure(0, weight=1)

        self.title_lbl = tk.Label(self.bottom_frame,
                                  text="High-Risk Forecast & Predicted Top Cause",
                                  font=("Segoe UI", 16, "bold"), bg=BG_APP, fg="#0F172A")
        self.title_lbl.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.table_canvas = tk.Canvas(self.bottom_frame, bg=BG_APP, highlightthickness=0)
        self.table_canvas.grid(row=1, column=0, sticky="nsew")
        self.table_canvas.bind("<Configure>", self._draw_bottom_table)

        self.columns = [
            ("Rank", 0.03),
            ("Machine", 0.16),
            ("Shift", 0.31),
            ("Predicted Scrap", 0.46),
            ("Risk Level", 0.66),
            ("Predicted Top Cause", 0.80),
        ]
        self.rows_data = []

    # ----- Actions -----
    def _reload_from_db(self):
        try:
            self.df_raw = fetch_logs()
            machines = ["All"] + (sorted(self.df_raw["machine_key"].unique().tolist())
                                  if not self.df_raw.empty else [])
            self.machine_cb["values"] = machines
            self.machine_cb.current(0)

            shifts = ["All"] + (sorted(self.df_raw["shift"].dropna().astype(str).str.upper().unique().tolist())
                                if not self.df_raw.empty else [])
            self.shift_cb["values"] = shifts
            self.shift_cb.current(0)

            self.apply_filters()
        except Exception as e:
            messagebox.showerror("Reload Error", str(e))

    def _export_dummy(self):
        messagebox.showinfo("Export", "Hook your export logic here (CSV/XLSX).")

    def apply_filters(self):
        if self.df_raw.empty:
            self._render_empty(); return

        df = self.df_raw.copy()

        m_sel = self.machine_cb.get()
        if m_sel and m_sel != "All":
            df = df[df["machine_key"] == m_sel]

        df = apply_date_preset(df, self.date_cb.get())

        s_sel = self.shift_cb.get()
        if s_sel and s_sel != "All":
            df = df[df["shift"].astype(str).str.upper() == s_sel]

        if df.empty:
            self._render_empty(); return

        day = df.groupby("date", as_index=False)["quantity"].sum().sort_values("date")
        y = day["quantity"].to_numpy(dtype=float)
        model = fit_predict_with_ci(y, periods_ahead=self.horizon_days)

        dates = day["date"].to_numpy()
        fut_dates = pd.date_range(
            start=(pd.to_datetime(dates[-1]) if len(dates) else pd.Timestamp.today()) + timedelta(days=1),
            periods=self.horizon_days, freq="D"
        )

        # Cause breakdown (tolerant if reason missing/blank)
        cause_df = df.assign(reason=df.get("reason", pd.Series(index=df.index)).replace({"": np.nan}))
        cause_df = cause_df.dropna(subset=["reason"])
        cause_agg = (cause_df.groupby("reason", as_index=False)["quantity"].sum()
                     .sort_values("quantity", ascending=False)) if not cause_df.empty else pd.DataFrame()

        # Risk rows
        self.rows_data = self._build_risk_rows(df)

        unit = (df["unit"].mode().iat[0] if "unit" in df.columns and not df["unit"].empty else "units")
        self._render_line_chart(dates, y, model, fut_dates, unit=unit)
        self._render_pie_chart(cause_agg)
        self._draw_bottom_table()

    # ----- Renderers -----
    def _render_empty(self):
        for child in self.chart_split.winfo_children():
            child.destroy()
        tk.Label(self.chart_split, text="No data for the selected filters.", bg=BG_APP,
                 font=("Segoe UI", 12)).grid(row=0, column=0, sticky="nsew")
        self.rows_data = []
        self._draw_bottom_table()

    def _render_line_chart(self, dates, y, model, fut_dates, unit=""):
        for child in self.chart_split.grid_slaves(row=0, column=0):
            child.destroy()

        fig_line = Figure(figsize=(6, 3), dpi=100)
        ax1 = fig_line.add_subplot(111)

        if len(y) <= 1:
            ax1.scatter(dates, y, label="Actual", color="#0078D7")
        else:
            ax1.plot(dates, y, "o--", label="Actual", color="#0078D7", linewidth=1.2)

        if len(model["y_pred"]) == len(dates) and len(model["y_pred"]):
            ax1.plot(dates, model["y_pred"], "-", label="Predicted", color="#1F8EFA", linewidth=2)
            if len(model["lower"]) == len(dates):
                ax1.fill_between(dates, model["lower"], model["upper"], alpha=0.2, color="#1F8EFA", label="Confidence")

        if len(fut_dates) and len(model["future_pred"]):
            ax1.plot(fut_dates, model["future_pred"], ":", color="#1F8EFA", linewidth=2, label="Forecast")
            if len(model["future_lower"]):
                ax1.fill_between(fut_dates, model["future_lower"], model["future_upper"], alpha=0.15, color="#1F8EFA")

        ax1.set_title(f"Predicted Scrap Volume ({unit})", fontsize=11)
        ax1.set_xlabel("Date")
        ax1.set_ylabel(f"Scrap ({unit})")
        ax1.grid(True, linestyle="--", alpha=0.35)
        ax1.legend()

        self.canvas_line = FigureCanvasTkAgg(fig_line, master=self.chart_split)
        self.canvas_line.draw()
        self.canvas_line.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        sep = tk.Frame(self.chart_split, bg="#B0B0B0", width=2)
        sep.grid(row=0, column=1, sticky="ns", padx=2)

    def _render_pie_chart(self, cause_agg: pd.DataFrame):
        for child in self.chart_split.grid_slaves(row=0, column=2):
            child.destroy()

        fig_pie = Figure(figsize=(5, 3), dpi=100)
        ax2 = fig_pie.add_subplot(111)

        if cause_agg is None or cause_agg.empty:
            ax2.axis("off")
            ax2.text(0.5, 0.5, "No scrap causes available\nin the selected window.",
                     ha="center", va="center", fontsize=11)
        else:
            total = float(cause_agg["quantity"].sum())
            if total <= 0:
                ax2.axis("off")
                ax2.text(0.5, 0.5, "No scrap causes available\nin the selected window.",
                         ha="center", va="center", fontsize=11)
            else:
                tmp = cause_agg.copy()
                tmp["share"] = tmp["quantity"] / total
                main = tmp[tmp["share"] >= 0.05].copy()
                other_sum = tmp[tmp["share"] < 0.05]["quantity"].sum()
                if other_sum > 0:
                    main = pd.concat([main,
                                      pd.DataFrame([{"reason": "Other",
                                                     "quantity": other_sum,
                                                     "share": other_sum/total}])],
                                     ignore_index=True)
                ax2.pie(main["quantity"], labels=main["reason"],
                        autopct="%1.0f%%", startangle=140, textprops={'fontsize': 9})
                ax2.set_title("Scrap Source Breakdown", fontsize=11)

        self.canvas_pie = FigureCanvasTkAgg(fig_pie, master=self.chart_split)
        self.canvas_pie.draw()
        self.canvas_pie.get_tk_widget().grid(row=0, column=2, sticky="nsew", padx=(5, 0))

    # ----- Risk table -----
    def _build_risk_rows(self, df: pd.DataFrame):
        if df.empty:
            return []

        last_date = df["date"].max()
        per_ms = (df[df["date"] == last_date]
                  .groupby(["machine_key", "shift"], as_index=False)["quantity"].sum())

        # Risk bucket + simple placeholder cause
        per_ms["Risk Level"] = per_ms["quantity"].apply(
            lambda x: risk_bucket(float(x or 0), self.threshold_low, self.threshold_high)
        )
        per_ms["Predicted Top Cause"] = "Material Defect"

        per_ms = per_ms.sort_values("quantity", ascending=False).reset_index(drop=True)
        # Adapt to drawing code: turn into list of dicts
        rows = []
        for i, r in per_ms.iterrows():
            rows.append({
                "rank": i + 1,
                "machine_key": str(r.get("machine_key", "")),
                "shift": str(r.get("shift", "")),
                "quantity": float(r.get("quantity", 0)),
                "Risk Level": r.get("Risk Level", "Low"),
                "Predicted Top Cause": r.get("Predicted Top Cause", "—"),
            })
        return rows[:10]

    def _draw_bottom_table(self, event=None):
        c = self.table_canvas
        c.delete("all")
        w = c.winfo_width() or 900

        if not self.rows_data:
            c.create_text(w/2, 24, text="No data available.", font=("Segoe UI", 11))
            return

        header_y = 12
        for text, relx in self.columns:
            x = int(w * relx)
            c.create_text(x, header_y, text=text, anchor="w",
                          font=("Segoe UI", 10, "bold"), fill="#475569")

        row_height = 28
        y = header_y + 24
        for i, row in enumerate(self.rows_data):
            # Rank
            c.create_text(int(w * self.columns[0][1]), y, anchor="w",
                          text=str(row.get("rank", i+1)), font=("Segoe UI", 10), fill="#0F172A")
            # Machine
            c.create_text(int(w * self.columns[1][1]), y, anchor="w",
                          text=row.get("machine_key", "—"), font=("Segoe UI", 10), fill="#0F172A")
            # Shift
            c.create_text(int(w * self.columns[2][1]), y, anchor="w",
                          text=row.get("shift", "—"), font=("Segoe UI", 10), fill="#0F172A")
            # Predicted Scrap (use quantity as proxy)
            pred_str = f"{int(float(row.get('quantity', 0))):,}"
            c.create_text(int(w * self.columns[3][1]), y, anchor="w",
                          text=pred_str, font=("Segoe UI", 10), fill="#0F172A")
            # Risk pill
            pill_w, pill_h = 70, 20
            rx = int(w * self.columns[4][1]); ry = y - pill_h // 2
            risk = row.get("Risk Level", "Low")
            color = RISK_COLORS.get(risk, "#6B7280")
            # rounded rect
            r = 8
            c.create_arc(rx, ry, rx + 2*r, ry + 2*r, start=90, extent=90, fill=color, outline="")
            c.create_arc(rx + pill_w - 2*r, ry, rx + pill_w, ry + 2*r, start=0, extent=90, fill=color, outline="")
            c.create_arc(rx, ry + pill_h - 2*r, rx + 2*r, ry + pill_h, start=180, extent=90, fill=color, outline="")
            c.create_arc(rx + pill_w - 2*r, ry + pill_h - 2*r, rx + pill_w, ry + pill_h, start=270, extent=90, fill=color, outline="")
            c.create_rectangle(rx + r, ry, rx + pill_w - r, ry + pill_h, fill=color, outline="")
            c.create_rectangle(rx, ry + r, rx + pill_w, ry + pill_h - r, fill=color, outline="")
            c.create_text(rx + pill_w/2, ry + pill_h/2, text=risk,
                          fill="white", font=("Segoe UI", 9, "bold"))
            # Cause
            c.create_text(int(w * self.columns[5][1]), y, anchor="w",
                          text=row.get("Predicted Top Cause", "—"),
                          font=("Segoe UI", 10), fill="#0F172A")

            y += row_height


# Back-compat alias used by main.py:
ViewPredictionsFrame = PredictionsDashboardFrame


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Scrap Predictions")
    root.geometry("1200x700")
    root.configure(bg=BG_APP)
    frame = PredictionsDashboardFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()
