import pandas as pd
import matplotlib.pyplot as plt

from config import (
    COMBINED_FOOD_DATA_CSV,
    CGM_RAW_DATA_CSV_FILE_ALL,
    EXERCISE_CSV,
)

exercise_path = EXERCISE_CSV
glucose_path = CGM_RAW_DATA_CSV_FILE_ALL
food_path = COMBINED_FOOD_DATA_CSV

# -----------------------------
# Load data
# -----------------------------
ex = pd.read_csv(exercise_path)
gl = pd.read_csv(glucose_path)
food = pd.read_csv(food_path)

# -----------------------------
# Parse timestamps
# -----------------------------
ex["start"] = pd.to_datetime(
    ex["Timestamp (YYYY-MM-DDThh:mm:ss)"]
)

gl["timestamp"] = pd.to_datetime(
    gl["Timestamp (YYYY-MM-DDThh:mm:ss)"]
)

gl["glucose"] = pd.to_numeric(
    gl["Glucose Value (mg/dL)"],
    errors="coerce"
)

gl = (
    gl
    .dropna(subset=["timestamp", "glucose"])
    .sort_values("timestamp")
)

# -----------------------------
# Find swimming sessions
# -----------------------------
swims = ex[
    ex["Event Subtype"]
    .astype(str)
    .str.lower()
    .eq("swim")
].copy()

# -----------------------------
# Find food timestamps
# -----------------------------
# Adjust this if your food timestamp column has a known name
food_time_col = next(
    c for c in food.columns
    if "time" in c.lower() or "date" in c.lower()
)

food[food_time_col] = pd.to_datetime(
    food[food_time_col],
    errors="coerce"
)

food_times = (
    food[food_time_col]
    .dropna()
    .sort_values()
    .tolist()
)

# -----------------------------
# Plot
# -----------------------------
fig, ax = plt.subplots(figsize=(10, 6))

for _, row in swims.iterrows():

    swim_start = row["start"]
    swim_end = swim_start + pd.Timedelta(hours=2)

    # Glucose readings during the 2-hour window
    glucose = gl[
        (gl["timestamp"] >= swim_start) &
        (gl["timestamp"] <= swim_end)
    ].copy()

    if len(glucose) == 0:
        continue

    glucose["minutes"] = (
        glucose["timestamp"] - swim_start
    ).dt.total_seconds() / 60

    # Food records occurring during this swim's 2-hour window
    meal_times = [
        t for t in food_times
        if swim_start <= t <= swim_end
    ]

    # Stop the plot at the first food intake within the window.
    plot_end = min(meal_times) if meal_times else swim_end
    plot_glucose = glucose[
        glucose["timestamp"] <= plot_end
    ].copy()

    if len(plot_glucose) == 0:
        continue

    plot_glucose["minutes"] = (
        plot_glucose["timestamp"] - swim_start
    ).dt.total_seconds() / 60

    ax.plot(
        plot_glucose["minutes"],
        plot_glucose["glucose"],
        linestyle="-",
        linewidth=1.2,
        alpha=0.55,
        label=swim_start.strftime("%b %-d")
    )

    # # ----------------------------------
    # # Mark food times
    # # ----------------------------------
    # for meal_time in meal_times:

    #     x = (
    #         meal_time - swim_start
    #     ).total_seconds() / 60

    #     ax.axvline(
    #         x,
    #         linestyle=":",
    #         linewidth=1,
    #         alpha=0.5
    #     )

# -----------------------------
# Formatting
# -----------------------------
ax.axvline(
    0,
    linestyle="--",
    linewidth=1
)

ax.set_xlim(0, 120)

ax.set_xlabel(
    "Minutes since swim session start"
)

ax.set_ylabel(
    "Glucose (mg/dL)"
)


ax.grid(
    True,
    alpha=0.25
)

ax.legend(
    title="Swim date",
    ncol=2
)

plt.tight_layout()
plt.show()