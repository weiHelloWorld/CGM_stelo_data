
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
    """Greedy non-overlap placement that also avoids covering other scatter points."""
    data = label_df.copy().reset_index(drop=True)
    n = len(data)
    if n == 0:
        return

    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # --- 1. Collect ALL scatter points in display (pixel) coordinates ---
    all_points_display = []
    for collection in ax.collections:
        if hasattr(collection, 'get_offsets'):
            for pt in collection.get_offsets():
                all_points_display.append(ax.transData.transform(pt))
    all_points_display = np.array(all_points_display)

    # --- 2. Generate candidate offsets (points) ---
    # Denser rings close to the point, sparser further out
    candidates = []
    np.random.seed(42)
    radii = [25, 40, 60, 85, 115, 150, 200, 260, 330, 420, 530, 660, 820, 1000]
    for r in radii:
        n_angles = max(16, int(2 * np.pi * r / 12))
        angles = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
        angles += np.random.uniform(0, 2 * np.pi / n_angles, size=len(angles))  # jitter
        for a in angles:
            candidates.append((r * np.cos(a), r * np.sin(a)))

    # --- 3. Pre-measure every label in display pixels ---
    label_sizes = []
    probes = []
    for _, row in data.iterrows():
        label = shorten_label(row["食物_中文"], 50)
        probe = ax.text(0.5, 0.5, label, fontsize=10, fontproperties=font_prop,
                        ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", alpha=0.85, ec="none"),
                        transform=ax.transAxes, visible=False)
        probes.append(probe)

    fig.canvas.draw()
    for probe in probes:
        br = probe.get_window_extent(renderer)
        label_sizes.append((br.width, br.height))
        probe.remove()

    # --- 4. Greedy placement ---
    placed_bboxes = []   # (x0, y0, x1, y1) in display pixels
    final_labels = []    # (label, x_data, y_data, ox_pt, oy_pt)

    for (_, row), (w, h) in zip(data.iterrows(), label_sizes):
        x, y = row[x_col], row[y_col]
        label = shorten_label(row["食物_中文"], 50)
        px, py = ax.transData.transform((x, y))   # data point in display pixels

        found = False
        for ox_pt, oy_pt in candidates:
            # Convert offset points -> display pixels
            cx = px + ox_pt * fig.dpi / 72.0
            cy = py + oy_pt * fig.dpi / 72.0
            x0, y0 = cx - w / 2, cy - h / 2
            x1, y1 = cx + w / 2, cy + h / 2

            pad_label = 4     # min space between two labels
            pad_point = 10    # min space between label and any scatter point
            pad_own   = 16    # extra clearance around the label's own data point

            # A. Don't cover its own point
            if (x0 - pad_own) < px < (x1 + pad_own) and (y0 - pad_own) < py < (y1 + pad_own):
                continue

            # B. Don't overlap already-placed labels
            overlap = False
            for pb in placed_bboxes:
                if (x0 - pad_label) < pb[2] and (x1 + pad_label) > pb[0] and \
                   (y0 - pad_label) < pb[3] and (y1 + pad_label) > pb[1]:
                    overlap = True
                    break
            if overlap:
                continue

            # C. Don't overlap OTHER scatter points
            pt_hit = False
            for pdx, pdy in all_points_display:
                if abs(pdx - px) < 2 and abs(pdy - py) < 2:
                    continue  # skip own point
                if (x0 - pad_point) < pdx < (x1 + pad_point) and (y0 - pad_point) < pdy < (y1 + pad_point):
                    pt_hit = True
                    break
            if pt_hit:
                continue

            # Accept
            placed_bboxes.append((x0, y0, x1, y1))
            final_labels.append((label, x, y, ox_pt, oy_pt))
            found = True
            break

        if not found:
            # Fallback: shove it far to the right so it doesn't block the cloud
            final_labels.append((label, x, y, 400, 0))

    # --- 5. Draw ---
    for label, x, y, ox, oy in final_labels:
        ax.annotate(label, xy=(x, y),
                    xytext=(ox, oy), textcoords="offset points",
                    fontsize=10, fontproperties=font_prop,
                    ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", lw=0.6, alpha=0.45, color="gray"),
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", alpha=0.85, ec="none"))


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
