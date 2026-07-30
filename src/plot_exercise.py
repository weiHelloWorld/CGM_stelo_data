import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
import helper

helper.setup_cjk_font()

from config import (
    COMBINED_FOOD_DATA_CSV,
    PROCESSED_CGM_CSV_FILE,
            EXERCISE_CSV,
    MG_DL_TO_MMOL_L, DOWNLOADS_DIR, UNIT, TEXT_LANGUAGE
)
from helper import localize

EXERCISE_TYPE_LABELS = {
    "swim": localize("游泳", "Swimming"),
    "resistance": localize("力量训练", "Resistance Training"),
}


def load_data(exercise_path, glucose_path, food_path):
    ex = pd.read_csv(exercise_path)
    gl = pd.read_csv(glucose_path)
    food = pd.read_csv(food_path)

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
    if UNIT == "mmol/L":
        gl["glucose"] = gl["glucose"] * MG_DL_TO_MMOL_L

    gl = (
        gl
        .dropna(subset=["timestamp", "glucose"])
        .sort_values("timestamp")
    )

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

    return ex, gl, food_times


def filter_sessions(exercise_df, exercise_types):
    normalized = [t.lower() for t in exercise_types]
    return exercise_df[
        exercise_df["Event Subtype"]
        .astype(str)
        .str.lower()
        .isin(normalized)
    ].copy()


def plot_exercise_on_ax(ax, sessions, glucose, food_times, exercise_type, window_hours=1.5):
    metrics = []

    if sessions.empty:
        subtitle = EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)
        ax.text(
            0.5,
            0.5,
            localize(f"未找到 {subtitle} 训练", f"No {subtitle} sessions found"),
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.set_axis_off()
        return metrics

    for _, row in sessions.iterrows():
        session_start = row["start"]
        session_end = session_start + pd.Timedelta(hours=window_hours)

        session_glucose = glucose[
            (glucose["timestamp"] >= session_start) &
            (glucose["timestamp"] <= session_end)
        ].copy()

        if session_glucose.empty:
            continue

        meal_times = [
            t for t in food_times
            if session_start <= t <= session_end
        ]

        plot_end = min(meal_times) if meal_times else session_end
        plot_glucose = session_glucose[
            session_glucose["timestamp"] <= plot_end
        ].copy()

        if plot_glucose.empty:
            continue

        plot_glucose = plot_glucose.sort_values("timestamp")
        plot_glucose["minutes"] = (
            plot_glucose["timestamp"] - session_start
        ).dt.total_seconds() / 60

        starting_glucose = float(plot_glucose.iloc[0]["glucose"])
        max_decrease = float(starting_glucose - plot_glucose["glucose"].min())
        metrics.append({
            "exercise_type": exercise_type,
            "starting_glucose": starting_glucose,
            "max_decrease": max(0.0, max_decrease),
            "date": session_start,
        })

        ax.plot(
            plot_glucose["minutes"],
            plot_glucose["glucose"],
            linestyle="-",
            linewidth=1.2,
            alpha=0.55,
        )

    ax.axvline(
        0,
        linestyle="--",
        linewidth=1
    )

    ax.set_xlim(0, window_hours * 60)
    ax.set_xlabel(localize("运动开始后分钟数", "Minutes after exercise start"))
    ax.set_ylabel(localize(f"血糖 ({UNIT})", f"Glucose ({UNIT})"))
    subtitle = EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)
    ax.set_title(localize(f"运动后 0–{window_hours} 小时的血糖变化 ({subtitle})", f"Glucose change 0–{window_hours}h after exercise ({subtitle})"))
    ax.grid(True, alpha=0.25)
    return metrics


if __name__ == "__main__":
    exercise_path = EXERCISE_CSV
    glucose_path = PROCESSED_CGM_CSV_FILE
    food_path = COMBINED_FOOD_DATA_CSV

    ex, gl, food_times = load_data(
        exercise_path,
        glucose_path,
        food_path,
    )

    exercise_types = ["swim", "resistance"]
    fig, axes = plt.subplots(1, 2, figsize=(20, 6), sharey=True)
    all_metrics = []

    for ax, exercise_type in zip(axes, exercise_types):
        sessions = filter_sessions(ex, [exercise_type])
        metrics = plot_exercise_on_ax(
            ax,
            sessions,
            gl,
            food_times,
            exercise_type,
            window_hours=1.5,
        )
        all_metrics.extend(metrics)

    scatter_fig, scatter_axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    scatter_fig.suptitle("Correlation between max_decrease and starting_glucose")

    for scatter_ax, exercise_type in zip(scatter_axes, exercise_types):
        subset_metrics = [m for m in all_metrics if m["exercise_type"] == exercise_type]
        if subset_metrics:
            starting_glucose = [m["starting_glucose"] for m in subset_metrics]
            max_decrease = [m["max_decrease"] for m in subset_metrics]
            dates = [m["date"] for m in subset_metrics]
            scatter_ax.scatter(
                starting_glucose,
                max_decrease,
                alpha=0.7,
                s=45,
                color="C0" if exercise_type == "swim" else "C1",
            )
            scatter_ax.set_xlabel("starting_glucose")
            scatter_ax.set_ylabel("max_decrease")

            for x, y, date_value in zip(starting_glucose, max_decrease, dates):
                scatter_ax.annotate(
                    date_value.strftime("%Y-%m-%d"),
                    (x, y),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=8,
                    alpha=0.8,
                )

            corr = pd.Series(starting_glucose).corr(pd.Series(max_decrease))
            corr_stat, p_value = pearsonr(starting_glucose, max_decrease)
            scatter_ax.set_title(
                f"{EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)}\n"
                f"corr = {corr_stat:.2f}, p = {p_value:.3g}"
            )
        else:
            scatter_ax.text(
                0.5,
                0.5,
                f"没有 {EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)} 的数据",
                ha="center",
                va="center",
                fontsize=12,
            )
            scatter_ax.set_axis_off()

        scatter_ax.grid(True, alpha=0.2)

    output_dir = DOWNLOADS_DIR
    os.makedirs(output_dir, exist_ok=True)

    fig_path = os.path.join(output_dir, "exercise_glucose_overview.png")
    scatter_path = os.path.join(output_dir, "exercise_correlation_scatter.png")

    fig.savefig(fig_path, dpi=300, bbox_inches="tight")
    scatter_fig.tight_layout(rect=[0, 0, 1, 0.96])
    scatter_fig.savefig(scatter_path, dpi=300, bbox_inches="tight")


