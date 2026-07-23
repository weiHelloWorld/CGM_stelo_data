import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

MG_DL_TO_MMOL_L = 1 / 18.0182

from analyze_cgm_2607 import GLOCOSE_RESPONSE_OUTPUT_CSV
from helper import setup_cjk_font
setup_cjk_font()

# 1. Load Data
df = pd.read_csv(GLOCOSE_RESPONSE_OUTPUT_CSV)

# 2. Date Parsing
df["Meal_Timestamp"] = pd.to_datetime(df["Meal_Timestamp"])

# 3. Apply Exclusion Filters
# Filter 1: Exclude "75g glucose" in Food column
df_filtered = df[
    ~df["Food"].str.contains("75g glucose", case=False, na=False)
].copy()

# Filter 2: Exclude "Mins Until Next Meal" < 120 (keep >= 120 or NaN)
df_filtered = df_filtered[
    (df_filtered["Mins Until Next Meal"] >= 120)
    | (df_filtered["Mins Until Next Meal"].isna())
]

# 4. Define Period Windows
period_1_start, period_1_end = pd.to_datetime("2026-06-16"), pd.to_datetime(
    "2026-07-01"
)
period_2_start, period_2_end = pd.to_datetime("2026-07-07"), pd.to_datetime(
    "2026-07-22"
)


def assign_period(dt):
    if period_1_start <= dt <= period_1_end + pd.Timedelta(days=1):
        return "Period 1 (2026-06-16 to 2026-07-01)"
    elif period_2_start <= dt <= period_2_end + pd.Timedelta(days=1):
        return "Period 2 (2026-07-07 to 2026-07-22)"
    return None


df_filtered["Period"] = df_filtered["Meal_Timestamp"].apply(assign_period)
df_plots = df_filtered.dropna(subset=["Period"]).copy()

df_plots["4h Avg Increase (mmol/L)"] = df_plots["4h Avg Increase"] * MG_DL_TO_MMOL_L
df_plots["2h Peak Increase (mmol/L)"] = df_plots["2h Peak Increase"] * MG_DL_TO_MMOL_L

# 5. Define Axes Variables
Y_COL = "2h Peak Increase (mmol/L)"
X_COL = "4h Avg Increase (mmol/L)"

# Meal Categories to Loop Through
meal_categories = {
    "All Meals": df_plots["餐次"].dropna().unique().tolist(),
    "早餐": ["早餐"],
    "午餐": ["午餐"],
    "晚餐": ["晚餐"],
    "加餐": ["加餐"],
}

# Color Palette for Periods
palette = {
    "Period 1 (2026-06-16 to 2026-07-01)": "#1f77b4",  # Blue
    "Period 2 (2026-07-07 to 2026-07-22)": "#ff7f0e",  # Orange
}

x_min = df_plots[X_COL].min()
x_max = df_plots[X_COL].max()
y_min = df_plots[Y_COL].min()
y_max = df_plots[Y_COL].max()

plot_min = min(x_min, y_min)
plot_max = max(x_max, y_max)
plot_margin = max((plot_max - plot_min) * 0.05, 0.1)

xlim = ylim = (plot_min - plot_margin, plot_max + plot_margin)

# 6. Generate Joint Scatter + Density Plots
for title, categories in meal_categories.items():
    subset = df_plots[df_plots["餐次"].isin(categories)].dropna(
        subset=[X_COL, Y_COL]
    )

    if subset.empty:
        print(f"No valid data points found for: {title}")
        continue

    # Main Joint Plot (Scatter only)
    g = sns.jointplot(
        data=subset,
        x=X_COL,
        y=Y_COL,
        hue="Period",
        palette=palette,
        kind="scatter",
        s=80,
        alpha=0.75,
        height=7,
    )

    # Top Marginal Density Distribution (4h Avg Increase)
    sns.kdeplot(
        data=subset,
        x=X_COL,
        hue="Period",
        palette=palette,
        ax=g.ax_marg_x,
        fill=True,
        alpha=0.3,
        legend=False,
    )

    # Right Marginal Density Distribution (2h Peak Increase)
    sns.kdeplot(
        data=subset,
        y=Y_COL,
        hue="Period",
        palette=palette,
        ax=g.ax_marg_y,
        fill=True,
        alpha=0.3,
        legend=False,
    )

    # Layout Customization
    g.fig.suptitle(
        f"{title}: {X_COL} vs. {Y_COL}", y=1.02, fontsize=14, fontweight="bold"
    )
    g.set_axis_labels(
        f"{X_COL}", f"{Y_COL}", fontsize=11, fontweight="bold"
    )
    g.ax_joint.set_xlim(xlim)
    g.ax_joint.set_ylim(ylim)
    g.ax_marg_x.set_xlim(xlim)
    g.ax_marg_y.set_ylim(ylim)

    output_path = f"/mnt/c/Users/weich/Downloads/{title.replace(' ', '_').replace('(', '').replace(')', '').replace(':', '')}.png"
    g.fig.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f'Saved plot to {output_path}')

    # plt.show()