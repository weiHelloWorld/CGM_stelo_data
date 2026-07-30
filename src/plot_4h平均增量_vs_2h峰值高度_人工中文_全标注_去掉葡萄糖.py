
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from config import MG_DL_TO_MMOL_L, UNIT, TEXT_LANGUAGE, DATA_DIR, DOWNLOADS_DIR
from helper import localize
from English_to_Chinese_map import convert_meal_name_language

PLOT_75G_GLUCOSE = False
glucose_file = str(DATA_DIR / "Clarity_Export_Chen_Wei_2026-07-03_145534.csv")
meal_file = str(DATA_DIR / "Food_track_202606.xlsx")

out_png = str(DOWNLOADS_DIR / ("4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖.png" if not PLOT_75G_GLUCOSE else "4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖_包括75g葡萄糖.png"))
out_csv = str(DOWNLOADS_DIR / ("每餐血糖指标_4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖.csv" if not PLOT_75G_GLUCOSE else "每餐血糖指标_4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖_包括75g葡萄糖.csv"))

font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_bold_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
font_prop = FontProperties(fname=font_path)
font_bold = FontProperties(fname=font_bold_path)
plt.rcParams["axes.unicode_minus"] = False

def load_glucose(path):
    raw = pd.read_csv(path)
    g = raw[raw["Event Type"] == "EGV"].copy()
    g["timestamp"] = pd.to_datetime(g["Timestamp (YYYY-MM-DDThh:mm:ss)"], errors="coerce")
    g["glucose"] = pd.to_numeric(g["Glucose Value (mg/dL)"], errors="coerce")
    if UNIT == "mmol/L":
        g["glucose"] = g["glucose"] * MG_DL_TO_MMOL_L
    g = g.dropna(subset=["timestamp", "glucose"]).sort_values("timestamp").reset_index(drop=True)
    return g[["timestamp", "glucose"]]

def load_meals(path):
    m = pd.read_excel(path, sheet_name=0)
    ts_col = "Meal_Timestamp" if "Meal_Timestamp" in m.columns else "timestamp"
    m[ts_col] = pd.to_datetime(m[ts_col], errors="coerce")
    m = m.dropna(subset=[ts_col]).sort_values(ts_col).reset_index(drop=True)
    m.rename(columns={ts_col: "timestamp"}, inplace=True)
    return m

def baseline_before_meal(glucose_df, meal_time, lookback_min=15):
    pre = glucose_df[
        (glucose_df["timestamp"] >= meal_time - pd.Timedelta(minutes=lookback_min)) &
        (glucose_df["timestamp"] < meal_time)
    ]
    if len(pre) > 0:
        return float(pre["glucose"].median())
    earlier = glucose_df[glucose_df["timestamp"] < meal_time]
    if len(earlier) > 0:
        return float(earlier.iloc[-1]["glucose"])
    return np.nan

def compute_window_metrics(glucose_df, meal_time, baseline, hours):
    end_time = meal_time + pd.Timedelta(hours=hours)
    w = glucose_df[(glucose_df["timestamp"] >= meal_time) & (glucose_df["timestamp"] <= end_time)].copy()
    if len(w) == 0 or pd.isna(baseline):
        return {"peak_inc": np.nan, "peak_time_min": np.nan, "avg_inc": np.nan, "valid_minutes": 0.0, "peak_timestamp": pd.NaT}

    w["minutes"] = (w["timestamp"] - meal_time).dt.total_seconds() / 60.0
    w["inc"] = w["glucose"] - baseline
    peak_idx = w["inc"].idxmax()
    peak_row = w.loc[peak_idx]

    if len(w) >= 2:
        valid_minutes = float(w["minutes"].iloc[-1] - w["minutes"].iloc[0])
        auc = float(np.trapz(w["inc"].to_numpy(), w["minutes"].to_numpy()))
        avg_inc = auc / valid_minutes if valid_minutes > 0 else float(w["inc"].mean())
    else:
        valid_minutes = 0.0
        avg_inc = float(w["inc"].iloc[0])

    return {
        "peak_inc": float(peak_row["inc"]),
        "peak_time_min": float(peak_row["minutes"]),
        "avg_inc": float(avg_inc),
        "valid_minutes": valid_minutes,
        "peak_timestamp": peak_row["timestamp"],
    }

def shorten_label(s, max_len=14):
    s = str(s)
    return s if len(s) <= max_len else s[:max_len - 1] + "…"


def translate_food(text):
    s = "" if pd.isna(text) else str(text).strip()
    return convert_meal_name_language(s)


def _place_labels(ax, label_df, font_prop, x_col="4h平均增量_mg_dL", y_col="2h峰值高度_mg_dL"):
    """Place labels with force-directed overlap removal, keeping them off data points."""
    data = label_df.copy().sort_values("标签优先级", ascending=False).reset_index(drop=True)
    n = len(data)
    if n == 0:
        return

    # --- 1. Initial radial spread ---
    np.random.seed(42)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    np.random.shuffle(angles)
    radii = np.linspace(35, 60, n)
    offsets = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])  # shape (n, 2) in offset points

    # --- 2. Create annotations at initial positions ---
    anns = []
    for i, (_, row) in enumerate(data.iterrows()):
        x, y = row[x_col], row[y_col]
        label = shorten_label(row["食物_中文"], 50)
        ann = ax.annotate(label, xy=(x, y), xytext=(offsets[i, 0], offsets[i, 1]),
                          textcoords="offset points",
                          fontsize=11, fontproperties=font_prop,
                          ha="center", va="center",
                          bbox=dict(boxstyle="round,pad=0.14", fc="white", alpha=0.78, ec="none"))
        anns.append(ann)

    # --- 3. Draw to get real pixel extents ---
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # Get display-coord centres of each data point (pixels)
    data_px = np.array([ax.transData.transform((row[x_col], row[y_col])) for _, row in data.iterrows()])

    def get_bboxes():
        """Return array of [[x0, y0, x1, y1], ...] in display pixel coords."""
        boxes = np.empty((n, 4))
        for i, ann in enumerate(anns):
            r = ann.get_window_extent(renderer)
            boxes[i] = [r.x0, r.y0, r.x1, r.y1]
        return boxes

    # --- 4. Force-directed iterations ---
    step = 8
    for _ in range(400):
        bboxes = get_bboxes()
        centres = np.column_stack([(bboxes[:, 0] + bboxes[:, 2]) / 2,
                                    (bboxes[:, 1] + bboxes[:, 3]) / 2])
        w2 = (bboxes[:, 2] - bboxes[:, 0]) / 2  # half-widths
        h2 = (bboxes[:, 3] - bboxes[:, 1]) / 2  # half-heights

        forces = np.zeros((n, 2))
        moved = False

        for i in range(n):
            # --- repulsion from other labels ---
            dx_l = centres[:, 0] - centres[i, 0]
            dy_l = centres[:, 1] - centres[i, 1]
            dist_l = np.sqrt(dx_l ** 2 + dy_l ** 2)
            overlap_x = (w2[i] + w2) - np.abs(dx_l)
            overlap_y = (h2[i] + h2) - np.abs(dy_l)
            overlapping = (overlap_x > 0) & (overlap_y > 0) & (dist_l > 0.1)
            if overlapping.any():
                dx = dx_l[overlapping]
                dy = dy_l[overlapping]
                d = np.maximum(np.sqrt(dx ** 2 + dy ** 2), 0.1)
                forces[i] -= np.array([np.sum(dx / d), np.sum(dy / d)])
                moved = True

            # --- attraction back toward own data point (medium spring) ---
            dp = centres[i] - data_px[i]
            dist_p = np.sqrt(dp[0] ** 2 + dp[1] ** 2)
            if dist_p > 5:
                forces[i] -= 0.01 * dp  # gentle pull back toward data point

        if not moved:
            break

        # Apply forces as pixel offsets, then convert back to offset points
        for i in range(n):
            # Get current offset in display pixels
            old_off_px = centres[i] - data_px[i]
            new_off_px = old_off_px + step * forces[i]
            # Clamp to avoid labels flying off screen
            new_off_px = np.clip(new_off_px, -800, 800)
            # Convert display pixels → offset points
            dpi_scale = fig.dpi / 72.0
            new_off_pt = new_off_px / dpi_scale
            offsets[i] = new_off_pt
            # Update annotation position
            anns[i].xyann = (new_off_pt[0], new_off_pt[1])

    # --- 5. Remove old and re-create with arrows ---
    for ann in anns:
        ann.remove()
    for i, (_, row) in enumerate(data.iterrows()):
        x, y = row[x_col], row[y_col]
        label = shorten_label(row["食物_中文"], 50)
        ox, oy = offsets[i]
        ax.annotate(label, xy=(x, y),
                    xytext=(ox, oy), textcoords="offset points",
                    fontsize=11, fontproperties=font_prop,
                    ha="left" if ox > 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", lw=0.42, alpha=0.35),
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", alpha=0.78, ec="none"))


glucose = load_glucose(glucose_file)
meals = load_meals(meal_file)

records = []
for i, meal in meals.iterrows():
    meal_time = meal["timestamp"]
    food = meal["Food"]
    next_time = meals.iloc[i+1]["timestamp"] if i < len(meals)-1 else pd.NaT

    baseline = baseline_before_meal(glucose, meal_time, 15)
    m2 = compute_window_metrics(glucose, meal_time, baseline, 2)
    m4 = compute_window_metrics(glucose, meal_time, baseline, 4)

    contam_2h_peak = bool(pd.notna(next_time) and pd.notna(m2["peak_timestamp"]) and next_time <= m2["peak_timestamp"])
    contam_4h_avg = bool(pd.notna(next_time) and next_time < meal_time + pd.Timedelta(hours=4))

    if contam_2h_peak and contam_4h_avg:
        pollution_tag = localize("双污染（已去掉）", "Both contaminated (removed)")
    elif contam_2h_peak:
        pollution_tag = localize("2h峰值污染", "2h peak contaminated")
    elif contam_4h_avg:
        pollution_tag = localize("4h平均污染", "4h avg contaminated")
    else:
        pollution_tag = localize("未污染", "Clean")

    records.append({
        "timestamp": meal_time,
        "食物": food,
        "食物_中文": translate_food(food),
        "2h峰值高度_mg_dL": m2["peak_inc"],
        "2h峰值可能污染": contam_2h_peak,
        "4h平均增量_mg_dL": m4["avg_inc"],
        "4h平均增量可能污染": contam_4h_avg,
        "污染标记": pollution_tag,
    })

result = pd.DataFrame(records)
plot_df = result[~((result["2h峰值可能污染"]) & (result["4h平均增量可能污染"]))].copy()
if not PLOT_75G_GLUCOSE:
    plot_df = plot_df[plot_df["食物"] != "75g glucose"].copy()
plot_df = plot_df.dropna(subset=["2h峰值高度_mg_dL", "4h平均增量_mg_dL"]).reset_index(drop=True)
plot_df["标签优先级"] = plot_df["2h峰值高度_mg_dL"] + 1.2 * plot_df["4h平均增量_mg_dL"]
label_df = plot_df.sort_values("标签优先级", ascending=False).reset_index(drop=True)
plot_df.to_csv(out_csv, index=False, encoding="utf-8-sig")

cat_clean = plot_df[(~plot_df["2h峰值可能污染"]) & (~plot_df["4h平均增量可能污染"])]
cat_peak_only = plot_df[(plot_df["2h峰值可能污染"]) & (~plot_df["4h平均增量可能污染"])]
cat_avg_only = plot_df[(~plot_df["2h峰值可能污染"]) & (plot_df["4h平均增量可能污染"])]

fig, ax = plt.subplots(figsize=(18, 13))
ax.scatter(cat_clean["4h平均增量_mg_dL"], cat_clean["2h峰值高度_mg_dL"], marker="o", s=55, label=localize("未污染", "Clean"))
ax.scatter(cat_avg_only["4h平均增量_mg_dL"], cat_avg_only["2h峰值高度_mg_dL"], marker="s", s=55, label=localize("只污染 4h 平均增量", "4h avg contaminated"))

_place_labels(ax, label_df, font_prop)

ax.set_xlabel(localize(f"4h 平均增量（{UNIT}）", f"4h Avg Increase ({UNIT})"), fontproperties=font_prop, fontsize=20)
ax.set_ylabel(localize(f"2h 峰值高度（{UNIT}）", f"2h Peak Height ({UNIT})"), fontproperties=font_prop, fontsize=20)
ax.set_title(localize("2h 峰值高度 vs 4h 平均增量", "2h Peak Height vs 4h Avg Increase"), fontproperties=font_bold, fontsize=20)
legend = ax.legend(prop=font_prop)
for text in legend.get_texts():
    text.set_fontproperties(font_prop)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(font_prop)
ax.grid(True, alpha=0.25)
plt.tight_layout()
plt.savefig(out_png, dpi=240, bbox_inches="tight")
# plt.show()
