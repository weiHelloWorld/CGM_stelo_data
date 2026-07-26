import pandas as pd
import matplotlib.pyplot as plt
import helper

helper.setup_cjk_font()

from config import (
    COMBINED_FOOD_DATA_CSV,
    CGM_RAW_DATA_CSV_FILE_ALL,
    EXERCISE_CSV,
    MG_DL_TO_MMOL_L,
)

EXERCISE_TYPE_LABELS = {
    "swim": "游泳",
    "resistance": "力量训练",
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
    ) * MG_DL_TO_MMOL_L

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


def plot_exercise_on_ax(ax, sessions, glucose, food_times, exercise_type, window_hours=2):
    if sessions.empty:
        subtitle = EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)
        ax.text(
            0.5,
            0.5,
            f"未找到 {subtitle} 训练",
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.set_axis_off()
        return

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

        plot_glucose["minutes"] = (
            plot_glucose["timestamp"] - session_start
        ).dt.total_seconds() / 60

        ax.plot(
            plot_glucose["minutes"],
            plot_glucose["glucose"],
            linestyle="-",
            linewidth=1.2,
            alpha=0.55,
            label=f"{session_start.month}月{session_start.day}日"
        )

    ax.axvline(
        0,
        linestyle="--",
        linewidth=1
    )

    ax.set_xlim(0, window_hours * 60)
    ax.set_xlabel("运动开始后分钟数")
    ax.set_ylabel("血糖 (mmol/L)")
    subtitle = EXERCISE_TYPE_LABELS.get(exercise_type, exercise_type)
    ax.set_title(f"运动后 0–{window_hours} 小时的血糖变化 ({subtitle})")
    ax.grid(True, alpha=0.25)
    ax.legend(title="日期", ncol=2)


if __name__ == "__main__":
    exercise_path = EXERCISE_CSV
    glucose_path = CGM_RAW_DATA_CSV_FILE_ALL
    food_path = COMBINED_FOOD_DATA_CSV

    ex, gl, food_times = load_data(
        exercise_path,
        glucose_path,
        food_path,
    )

    exercise_types = ["swim", "resistance"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

    for ax, exercise_type in zip(axes, exercise_types):
        sessions = filter_sessions(ex, [exercise_type])
        plot_exercise_on_ax(
            ax,
            sessions,
            gl,
            food_times,
            exercise_type,
            window_hours=2,
        )

    plt.tight_layout()
    plt.show()
