# view_predictions.py — SQLite Recruiter Edition (runs with sample data)
from dotenv import load_dotenv
load_dotenv()

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from db import get_db_connection

# -----------------
# SETTINGS / THEME
# -----------------
FILTER_BG = "#DCDAD5"
RISK_COLORS = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#22C55E"}
BG_SIDEBAR = "#DBE2E9"
BG_APP = "white"


# -----------------
# DB (SQLite version)
# -----------------
def fetch_logs() -> pd.DataFrame:
    """
    Fetch scrap logs from the local SQLite database (demo-safe).
    Automatically adapts columns and normalizes values.
    """
    with get_db_connection() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(scrap_logs)").fetchall()}
        sel_cols = ["date", "quantity", "unit", "shift", "reason"]
        if "machine_name" in cols:
            sel_cols.insert(0, "machine_name")
        elif "machine_operator" in cols:
            sel_cols.insert(0, "machine_operator")
        if "comments" in cols:
            sel_cols.append("comments")
        qry = f"SELECT {', '.join(sel_cols)} FROM scrap_logs"
        rows = [dict(r) for r in conn.execute(qry).fetchall()]

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit"] = df["unit"].astype(str)
    df["shift"] = df["shift"].astype(str).str.strip().str.upper()
    df["reason"] = df.get("reason", pd.Series(index=df.index)).astype(str).str.strip()

    if "machine_name" in df.columns:
        df["machine_key"] = df["machine_name"].astype(str)
    elif "machine_operator" in df.columns:
        df["machine_key"] = df["machine_operator"].astype(str)
    else:
        df["machine_key"] = "Unknown"

    df = df.dropna(subset=["date", "quantity", "unit", "shift", "machine_key"])
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
        resid = np.pad(resid, (0, 5 - len(resid)), constant_values=resid.mean())

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

        self.df_raw = fetch_logs()
        self.horizon_days = 7
        self.threshold_low = 2500
        self.threshold_high = 4000

        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_top_controls()
        self._build_split_charts()
        self._build_bottom_table()
        self.apply_filters()

    # Sidebar -------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self, bg=BG_SIDEBAR, padx=10, pady=10)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="ns")
        self.sidebar.columnconfigure(0, weight=1)

        tk.Label(self.sidebar, text="Filters", font=("Segoe UI", 12, "bold"), bg=BG_SIDEBAR).pack(anchor="w", pady=(0, 10))

        tk.Label(self.sidebar, text="Machine:", bg=BG_SIDEBAR).pack(anchor="w")
        machines = ["All"]
        if not self.df_raw.empty:
            machines += sorted(self.df_raw["machine_key"].dropna().unique().tolist())
        self.machine_cb = ttk.Combobox(self.sidebar, values=machines, state="readonly", style="Custom.TCombobox")
        self.machine_cb.current(0)
        self.machine_cb.pack(fill="x", pady=5)

        tk.Label(self.sidebar, text="Date:", bg=BG_SIDEBAR).pack(anchor="w", pady=(10, 0))
        self.date_cb = ttk.Combobox(self.sidebar, values=["Today", "This Week", "This Month", "Last 30 Days"],
                                    state="readonly", style="Custom.TCombobox")
        self.date_cb.current(3)
        self.date_cb.pack(fill="x", pady=5)

        tk.Label(self.sidebar, text="Shift:", bg=BG_SIDEBAR).pack(anchor="w", pady=(10, 0))
        shifts = ["All"]
        if not self.df_raw.empty:
            shifts += sorted(self.df_raw["shift"].dropna().unique().tolist())
        self.shift_cb = ttk.Combobox(self.sidebar, values=shifts, state="readonly", style="Custom.TCombobox")
        self.shift_cb.current(0)
        self.shift_cb.pack(fill="x", pady=5)

        ttk.Button(self.sidebar, text="Apply Filters", command=self.apply_filters).pack(fill="x", pady=(20, 0))
        ttk.Button(self.sidebar, text="Reload from DB", command=self._reload_from_db).pack(fill="x", pady=(8, 0))

    # Controls / Charts / Table ------------------------------------------
    def _build_top_controls(self):
        self.top_controls = tk.Frame(self, bg=BG_APP, padx=10, pady=10)
        self.top_controls.grid(row=0, column=1, sticky="ew")
        self.top_controls.columnconfigure(0, weight=1)

        tk.Label(self.top_controls, text="Scrap Predictions", font=("Segoe UI", 14, "bold"), bg=BG_APP).pack(side="left")
        ttk.Button(self.top_controls, text="Export Data", command=self._export_dummy).pack(side="right", padx=5)
        ttk.Button(self.top_controls, text="Refresh", command=self.apply_filters).pack(side="right", padx=5)

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

        self.title_lbl = tk.Label(self.bottom_frame, text="High-Risk Forecast & Predicted Top Cause",
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

    # Actions --------------------------------------------------------------
    def _reload_from_db(self):
        try:
            self.df_raw = fetch_logs()
            machines = ["All"] + (sorted(self.df_raw["machine_key"].unique().tolist()) if not self.df_raw.empty else [])
            self.machine_cb["values"] = machines
            self.machine_cb.current(0)

            shifts = ["All"] + (sorted(self.df_raw["shift"].dropna().unique().tolist()) if not self.df_raw.empty else [])
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
            df = df[df["shift"] == s_sel]

        if df.empty:
            self._render_empty(); return

        day = df.groupby("date", as_index=False)["quantity"].sum().sort_values("date")
        y = day["quantity"].to_numpy(dtype=float)
        model = fit_predict_with_ci(y, periods_ahead=self.horizon_days)
        dates = day["date"].to_numpy()
        fut_dates = pd.date_range(start=pd.to_datetime(dates[-1]) + timedelta(days=1),
                                  periods=self.horizon_days, freq="D")

        cause_df = df.assign(reason=df["reason"].replace({"": np.nan})).dropna(subset=["reason"])
        cause_agg = (cause_df.groupby("reason", as_index=False)["quantity"].sum()
                     .sort_values("quantity", ascending=False))

        self.rows_data = self._build_risk_rows(df)

        unit = df["unit"].mode().iat[0] if not df["unit"].empty else ""
        self._render_line_chart(dates, y, model, fut_dates, unit=unit)
        self._render_pie_chart(cause_agg)
        self._draw_bottom_table()

    # Chart Rendering ------------------------------------------------------
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

        if len(y) == 1:
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

        if cause_agg.empty:
            ax2.axis("off")
            ax2.text(0.5, 0.5, "No scrap causes available\nin the selected window.",
                     ha="center", va="center", fontsize=11)
        else:
            total = cause_agg["quantity"].sum()
            cause_agg["share"] = cause_agg["quantity"] / total
            main = cause_agg[cause_agg["share"] >= 0.05]
            other_sum = cause_agg[cause_agg["share"] < 0.05]["quantity"].sum()
            if other_sum > 0:
                main = pd.concat([main, pd.DataFrame([{"reason": "Other", "quantity": other_sum, "share": other_sum / total}])])
            ax2.pie(main["quantity"], labels=main["reason"], autopct="%1.0f%%", startangle=140, textprops={'fontsize': 9})
            ax2.set_title("Scrap Source Breakdown", fontsize=11)

        self.canvas_pie = FigureCanvasTkAgg(fig_pie, master=self.chart_split)
        self.canvas_pie.draw()
        self.canvas_pie.get_tk_widget().grid(row=0, column=2, sticky="nsew", padx=(5, 0))

    # Risk Table -----------------------------------------------------------
    def _build_risk_rows(self, df: pd.DataFrame):
        last_date = df["date"].max()
        per_ms = (df[df["date"] == last_date]
                  .groupby(["machine_key", "shift"], as_index=False)["quantity"].sum())
        per_ms["Risk Level"] = per_ms["quantity"].apply(
            lambda x: risk_bucket(x, self.threshold_low, self.threshold_high))
        per_ms["Predicted Top Cause"] = "Material Defect"
        per_ms.sort_values("quantity", ascending=False, inplace=True)
        per_ms.reset_index(drop=True, inplace=True)
        return per_ms.to_dict("records")

    def _draw_bottom_table(self, event=None):
        self.table_canvas.delete("all")
        if not self.rows_data:
            self.table_canvas.create_text(self.table_canvas.winfo_width() / 2,
                                          40, text="No data available.",
                                          font=("Segoe UI", 11))
            return
        w = self.table_canvas.winfo_width()
        y = 15
        for name, relx in self.columns:
            self.table_canvas.create_text(w * relx, y, text=name,
                                          font=("Segoe UI", 11, "bold"), anchor="w")
        y += 25
        for i, row in enumerate(self.rows_data):
            color = "#F7F9FB" if i % 2 == 0 else "white"
            self.table_canvas.create_rectangle(0, y - 12, w, y + 12, fill=color, outline="")
            self.table_canvas.create_text(w * self.columns[0][1], y, text=str(i + 1), anchor="w", font=("Segoe UI", 10))
            self.table_canvas.create_text(w * self.columns[1][1], y, text=row.get("machine_key", ""), anchor="w", font=("Segoe UI", 10))
            self.table_canvas.create_text(w * self.columns[2][1], y, text=row.get("shift", ""), anchor="w", font=("Segoe UI", 10))
            self.table_canvas.create_text(w * self.columns[3][1], y, text=f"{row.get('quantity', 0):,.0f}", anchor="w", font=("Segoe UI", 10))
            risk = row.get("Risk Level", "Low")
            color = RISK_COLORS.get(risk, "#22C55E")
            self.table_canvas.create_text(w * self.columns[4][1], y, text=risk, fill=color, anchor="w", font=("Segoe UI", 10, "bold"))
            self.table_canvas.create_text(w * self.columns[5][1], y, text=row.get("Predicted Top Cause", ""), anchor="w", font=("Segoe UI", 10))
            y += 25


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Scrap Predictions")
    frame = PredictionsDashboardFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()
