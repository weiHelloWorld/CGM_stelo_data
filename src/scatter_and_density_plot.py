import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from analyze_cgm_2607 import GLOCOSE_RESPONSE_OUTPUT_CSV

# Set style and Chinese font support
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid")

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

# 5. Define Axes Variables
Y_COL = "2h Peak Increase"
X_COL = "4h Avg Increase"

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

# 6. Generate Joint Scatter + Density Plots
for title, categories in meal_categories.items():
    subset = df_plots[df_plots["餐次"].isin(categories)].dropna(
        subset=[X_COL, Y_COL]
    )

    if subset.empty:
        print(f"No valid data points found for: {title}")
        continue

    # Main Joint Plot (Scatter + Marginal Density Distributions)
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

    # 2D KDE Contours on Main Plot Area
    sns.kdeplot(
        data=subset,
        x=X_COL,
        y=Y_COL,
        hue="Period",
        palette=palette,
        ax=g.ax_joint,
        levels=4,
        alpha=0.4,
        linewidths=1.5,
        legend=False,
    )

    # Top Marginal Density Distribution (2h Peak Increase)
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

    # Right Marginal Density Distribution (4h Avg Increase)
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
        f"{X_COL} (mg/dL)", f"{Y_COL} (mg/dL)", fontsize=11, fontweight="bold"
    )

    plt.show()