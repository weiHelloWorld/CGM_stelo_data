
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

PLOT_75G_GLUCOSE = True
glucose_file = r"./Clarity_Export_Chen_Wei_2026-07-03_145534.csv"
meal_file = r"./Stelo_CGM_餐食记录模板.xlsx"

out_png = r"./output/4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖.png" if not PLOT_75G_GLUCOSE else r"./output/4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖_包括75g葡萄糖.png"
out_csv = r"./output/每餐血糖指标_4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖.csv" if not PLOT_75G_GLUCOSE else r"./output/每餐血糖指标_4h平均增量_vs_2h峰值高度_人工中文_全标注_去掉葡萄糖_包括75g葡萄糖.csv"

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
    g = g.dropna(subset=["timestamp", "glucose"]).sort_values("timestamp").reset_index(drop=True)
    return g[["timestamp", "glucose"]]

def load_meals(path):
    m = pd.read_excel(path, sheet_name=0)
    m["timestamp"] = pd.to_datetime(m["timestamp"], errors="coerce")
    m = m.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
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

EXACT_FOOD_MAP = {
    "三峡人家跳跳鱼": "三峡人家跳跳鱼",
    "lettuce, 200g tofu, 2% fat milk": "生菜、豆腐 200g、2% 牛奶",
    "chobani zero sugar yogurt + orange + 2% fat milk": "Chobani 零糖酸奶、橙子、2% 牛奶",
    "1/2 cup oats + 250 mL 2% milk + 15 g protein powder": "半杯燕麦、250mL 2% 牛奶、15g 蛋白粉",
    "pasta with tomato sauce and pork": "番茄猪肉意面",
    "chobani zero sugar yogurt": "Chobani 零糖酸奶",
    "yakult light drink": "低糖养乐多",
    "lettuce, imitation crab meat, pistachios": "生菜、蟹肉棒、开心果",
    "Oatmeal, milk, protein powder": "燕麦、牛奶、蛋白粉",
    "Chow mein, mushroom chicken, Beijing beef": "炒面、蘑菇鸡、北京牛",
    "Apple": "苹果",
    "Lettuce, fish tofu": "生菜、鱼豆腐",
    "chobani zero sugar yogurt + pistachios": "Chobani 零糖酸奶、开心果",
    "1/2 cup of oatmeal with protein powder and milk": "半杯燕麦、蛋白粉、牛奶",
    "Pistachio": "开心果",
    "Pepperoni pizza": "意式辣香肠披萨",
    "Eggs, Pocky": "鸡蛋、百奇",
    "oikos triple zero mixed berry + 2% fat milk": "Oikos 三零混合莓酸奶、2% 牛奶",
    "Half cup of oatmeal, milk, and protein powder": "半杯燕麦、牛奶、蛋白粉",
    "Weee 半份辣子鸡": "Weee 半份辣子鸡",
    "Weee 盐水鸭半份": "Weee 半份盐水鸭",
    "Swiss roll": "瑞士卷",
    "oikos triple zero mixed berry": "Oikos 三零混合莓酸奶",
    "3/8 cup oatmeal, milk, protein powder": "3/8 杯燕麦、牛奶、蛋白粉",
    "zero suger coke": "零糖可乐",
    "Kung Pao chicken with white rice": "宫保鸡丁配白米饭",
    "Oikos Triple Zero strawberry flavored nonfat yogurt, 2% fat milk": "Oikos 三零草莓酸奶、2% 牛奶",
    "1/2 cup of oats, milk, protein powder": "半杯燕麦、牛奶、蛋白粉",
    "Weee 半份盐水鸭，瑞士卷": "Weee 半份盐水鸭、瑞士卷",
    "Mixed berry Oikos Triple Zero yogurt": "Oikos 三零混合莓酸奶",
    "螺蛳粉 2/3 粉包，猪肉，包菜": "螺蛳粉 2/3 粉包、猪肉、包菜",
    "Pistachio, Oikos Triple Zero yogurt, milk": "开心果、Oikos 三零酸奶、牛奶",
    "1/2 cup oats, milk, protein powder": "半杯燕麦、牛奶、蛋白粉",
    "2 eggs, instant ramen": "2 个鸡蛋、方便面",
    "辛拉面，猪肉，海带": "辛拉面、猪肉、海带",
    "Oikos Triple Zero strawberry flavored yogurt": "Oikos 三零草莓酸奶",
    "1/2 oatmeal, milk, protein powder": "半份燕麦、牛奶、蛋白粉",
    "Sardine, 300g sweet potato": "沙丁鱼、300g 红薯",
    "Lettuce, 半份 pork bbq": "生菜、半份叉烧",
    "Orange, Oikos yogurt, milk": "橙子、Oikos 酸奶、牛奶",
    "1/2 cup oatmeal, milk, protein powder": "半杯燕麦、牛奶、蛋白粉",
    "Half pork bbq, Swiss roll": "半份叉烧、瑞士卷",
    "包菜，虾，螺蛳粉（2/3 粉包）": "包菜、虾、螺蛳粉（2/3 粉包）",
    "Orange, yogurt, milk": "橙子、酸奶、牛奶",
    "1/2 pizza": "半个披萨",
    "1/2 烤鸭，瑞士卷": "半份烤鸭、瑞士卷",
    "Chobani yogurt, milk": "Chobani 酸奶、牛奶",
    "75g glucose": "75g 葡萄糖",
    "190g 炒饭，开心果": "190g 炒饭、开心果",
    "Pistachios, Chobani yogurt": "开心果、Chobani 酸奶",
    "6 shrimp tempura, Swiss roll": "6 只炸虾天妇罗、瑞士卷",
    "Orange, Chobani yogurt": "橙子、Chobani 酸奶",
    "6 shrimp tempura, Chobani yogurt": "6 只炸虾天妇罗、Chobani 酸奶",
    "开心果": "开心果",
    "75g pasta with tomato sauce, shrimp, mushrooms": "75g 番茄虾仁蘑菇意面",
    "Orange, milk": "橙子、牛奶",
    "鱼豆腐，包菜，蘑菇，苹果": "鱼豆腐、包菜、蘑菇、苹果",
    "2/3 螺蛳粉，生菜，蘑菇，鸡蛋": "2/3 螺蛳粉、生菜、蘑菇、鸡蛋",
    "肉松，Chobani yogurt，milk": "肉松、Chobani 酸奶、牛奶",
}

def translate_food(text):
    s = "" if pd.isna(text) else str(text).strip()
    return EXACT_FOOD_MAP.get(s, s)

glucose = load_glucose(glucose_file)
meals = load_meals(meal_file)

records = []
for i, meal in meals.iterrows():
    meal_time = meal["timestamp"]
    food = meal["食物"] if "食物" in meals.columns else f"第{i+1}餐"
    next_time = meals.iloc[i+1]["timestamp"] if i < len(meals)-1 else pd.NaT

    baseline = baseline_before_meal(glucose, meal_time, 15)
    m2 = compute_window_metrics(glucose, meal_time, baseline, 2)
    m4 = compute_window_metrics(glucose, meal_time, baseline, 4)

    contam_2h_peak = bool(pd.notna(next_time) and pd.notna(m2["peak_timestamp"]) and next_time <= m2["peak_timestamp"])
    contam_4h_avg = bool(pd.notna(next_time) and next_time < meal_time + pd.Timedelta(hours=4))

    if contam_2h_peak and contam_4h_avg:
        pollution_tag = "双污染（已去掉）"
    elif contam_2h_peak:
        pollution_tag = "2h峰值污染"
    elif contam_4h_avg:
        pollution_tag = "4h平均污染"
    else:
        pollution_tag = "未污染"

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
    plot_df = plot_df[plot_df["食物_中文"] != "75g 葡萄糖"].copy()
plot_df = plot_df.dropna(subset=["2h峰值高度_mg_dL", "4h平均增量_mg_dL"]).reset_index(drop=True)
plot_df["标签优先级"] = plot_df["2h峰值高度_mg_dL"] + 1.2 * plot_df["4h平均增量_mg_dL"]
label_df = plot_df.sort_values("标签优先级", ascending=False).reset_index(drop=True)
plot_df.to_csv(out_csv, index=False, encoding="utf-8-sig")

cat_clean = plot_df[(~plot_df["2h峰值可能污染"]) & (~plot_df["4h平均增量可能污染"])]
cat_peak_only = plot_df[(plot_df["2h峰值可能污染"]) & (~plot_df["4h平均增量可能污染"])]
cat_avg_only = plot_df[(~plot_df["2h峰值可能污染"]) & (plot_df["4h平均增量可能污染"])]

fig, ax = plt.subplots(figsize=(18, 13))
ax.scatter(cat_clean["4h平均增量_mg_dL"], cat_clean["2h峰值高度_mg_dL"], marker="o", s=55, label="未污染")
ax.scatter(cat_peak_only["4h平均增量_mg_dL"], cat_peak_only["2h峰值高度_mg_dL"], marker="^", s=75, label="只污染 2h 峰值")
ax.scatter(cat_avg_only["4h平均增量_mg_dL"], cat_avg_only["2h峰值高度_mg_dL"], marker="s", s=75, label="只污染 4h 平均增量")

placed = []
for _, row in label_df.iterrows():
    x = row["4h平均增量_mg_dL"]
    y = row["2h峰值高度_mg_dL"]
    # suffix = "（2h?）" if row["2h峰值可能污染"] else ("（4h?）" if row["4h平均增量可能污染"] else "")
    label = shorten_label(row["食物_中文"], 14) # + suffix
    candidates = [
        (0.5, 0.9), (0.9, -1.0), (-0.9, 1.0), (-0.9, -1.0),
        (1.4, 0.2), (-1.4, 0.2), (0.2, 1.7), (0.2, -1.7),
        (1.8, 1.2), (-1.8, 1.2), (1.8, -1.2), (-1.8, -1.2),
        (2.3, 0.0), (-2.3, 0.0), (0.0, 2.4), (0.0, -2.4),
        (2.8, 1.3), (-2.8, 1.3), (2.8, -1.3), (-2.8, -1.3),
        (3.2, 0.8), (-3.2, 0.8), (3.2, -0.8), (-3.2, -0.8),
        (3.8, 0.0), (-3.8, 0.0), (0.0, 3.2), (0.0, -3.2),
    ]
    best = None
    best_score = None
    for dx, dy in candidates:
        tx, ty = x + dx, y + dy
        min_dist = min([((tx - px) ** 2 + ((ty - py) * 0.9) ** 2) ** 0.5 for px, py in placed], default=999.0)
        penalty = ((dx**2 + dy**2)**0.5) * 0.12
        score = min_dist - penalty
        if best_score is None or score > best_score:
            best_score = score
            best = (dx, dy)
    dx, dy = best
    tx, ty = x + dx, y + dy
    placed.append((tx, ty))
    ax.annotate(label, xy=(x, y), xytext=(tx, ty), textcoords="data",
                fontsize=7.8, fontproperties=font_prop,
                ha="left" if dx >= 0 else "right", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.42, alpha=0.35),
                bbox=dict(boxstyle="round,pad=0.14", fc="white", alpha=0.78, ec="none"))

ax.set_xlabel("4h 平均增量（mg/dL）", fontproperties=font_prop, fontsize=20)
ax.set_ylabel("2h 峰值高度（mg/dL）", fontproperties=font_prop, fontsize=20)
ax.set_title("2h 峰值高度 vs 4h 平均增量", fontproperties=font_bold, fontsize=20)
legend = ax.legend(prop=font_prop)
for text in legend.get_texts():
    text.set_fontproperties(font_prop)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(font_prop)
ax.grid(True, alpha=0.25)
plt.tight_layout()
plt.savefig(out_png, dpi=240, bbox_inches="tight")
plt.show()
