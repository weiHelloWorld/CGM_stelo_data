
# %%
import argparse
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from helper import setup_cjk_font

from config import COMBINED_FOOD_DATA_CSV, DEFAULT_CGM_CSV, GLOCOSE_RESPONSE_OUTPUT_CSV, MG_DL_TO_MMOL_L, UNIT

def parse_args():
    parser = argparse.ArgumentParser(description="Analyze CGM glucose response by meal.")
    parser.add_argument(
        "--cgm",
        default=DEFAULT_CGM_CSV,
        help=f"Path to CGM Clarity export CSV (default: {DEFAULT_CGM_CSV})",
    )
    parser.add_argument(
        "--food",
        default=COMBINED_FOOD_DATA_CSV,
        help=f"Path to combined food data CSV (default: {COMBINED_FOOD_DATA_CSV})",
    )
    return parser.parse_args()


def normalize_meal_time(value):
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return s
    digits = re.sub(r"\D", "", s)
    if len(digits) == 3:
        return f"0{digits[0]}:{digits[1:]}"
    elif len(digits) == 4:
        return f"{digits[:2]}:{digits[2:]}"
    else:
        raise Exception(f"Invalid time format: {s}")


def main(cgm_csv_file, food_csv_file):
    # 1. Load the Data
    food_df = pd.read_csv(food_csv_file)
    cgm_df = pd.read_csv(cgm_csv_file)

    # 2. Clean and Parse Food Log
    food_df["Meal_Timestamp"] = pd.to_datetime(food_df["Meal_Timestamp"])
    food_df = food_df.dropna(subset=["Food", "Meal_Timestamp"]).reset_index(drop=True)
    food_df = food_df.sort_values("Meal_Timestamp").reset_index(drop=True)
    food_df["Mins Since Prev Meal"] = (
        food_df["Meal_Timestamp"] - food_df["Meal_Timestamp"].shift(1)
    ).dt.total_seconds() / 60
    food_df["Mins Until Next Meal"] = (
        food_df["Meal_Timestamp"].shift(-1) - food_df["Meal_Timestamp"]
    ).dt.total_seconds() / 60

    # 3. Clean and Parse CGM Data
    cgm_df = cgm_df[cgm_df["Event Type"] == "EGV"].copy()
    cgm_df["Timestamp"] = pd.to_datetime(cgm_df["Timestamp (YYYY-MM-DDThh:mm:ss)"])
    cgm_df["Glucose"] = pd.to_numeric(cgm_df["Glucose Value (mg/dL)"], errors="coerce")
    if UNIT == "mmol/L":
        cgm_df["Glucose"] = cgm_df["Glucose"] * MG_DL_TO_MMOL_L
    cgm_df = cgm_df.dropna(subset=["Glucose"]).sort_values("Timestamp")

    # 4. Calculate Post-Meal Metrics
    results = []

    for _, meal in food_df.iterrows():
        meal_time = meal["Meal_Timestamp"]

        pre_meal_start = meal_time - pd.Timedelta(minutes=15)
        pre_meal_end = meal_time + pd.Timedelta(minutes=5)
        post_2h_end = meal_time + pd.Timedelta(hours=2)
        post_4h_end = meal_time + pd.Timedelta(hours=4)

        pre_cgm = cgm_df[
            (cgm_df["Timestamp"] >= pre_meal_start) & (cgm_df["Timestamp"] <= pre_meal_end)
        ]
        if pre_cgm.empty:
            continue

        pre_glucose = pre_cgm.iloc[
            (pre_cgm["Timestamp"] - meal_time).abs().argsort()[:1]
        ]["Glucose"].values[0]

        cgm_2h = cgm_df[(cgm_df["Timestamp"] > meal_time) & (cgm_df["Timestamp"] <= post_2h_end)]
        cgm_4h = cgm_df[(cgm_df["Timestamp"] > meal_time) & (cgm_df["Timestamp"] <= post_4h_end)]

        target_1h = meal_time + pd.Timedelta(hours=1)
        target_2h = meal_time + pd.Timedelta(hours=2)

        glucose_1h = np.nan
        glucose_2h = np.nan
        if not cgm_df.empty:
            glucose_1h = cgm_df.iloc[(cgm_df["Timestamp"] - target_1h).abs().argsort()[:1]]["Glucose"].values[0]
            glucose_2h = cgm_df.iloc[(cgm_df["Timestamp"] - target_2h).abs().argsort()[:1]]["Glucose"].values[0]

        peak_2h_delta = (cgm_2h["Glucose"].max() - pre_glucose) if not cgm_2h.empty else np.nan
        avg_4h_delta = (cgm_4h["Glucose"].mean() - pre_glucose) if not cgm_4h.empty else np.nan
        i_res = meal.to_dict()
        i_res.update(
            {
                "Pre-Meal Glucose": pre_glucose,
                "1h Glucose": glucose_1h,
                "2h Glucose": glucose_2h,
                "2h Peak Increase": peak_2h_delta,
                "4h Avg Increase": avg_4h_delta,
            }
        )
        results.append(i_res)

    # 5. Output Results
    output_df = pd.DataFrame(results)
    output_path = Path(
        GLOCOSE_RESPONSE_OUTPUT_CSV
    )
    output_df.to_csv(output_path, index=False)

    font_prop = setup_cjk_font()
    sns.set_theme(style="whitegrid")

    plot_df = output_df.dropna(subset=["2h Peak Increase", "4h Avg Increase"]).copy()
    if plot_df.empty:
        print("No valid points available for plotting.")
        return

    plt.figure(figsize=(12, 8))

    sns.scatterplot(
        data=plot_df,
        x="4h Avg Increase",
        y="2h Peak Increase",
        alpha=0.6,
        s=100,
        color="teal",
        edgecolor="w",
        linewidth=1,
    )

    for _, row in plot_df.iterrows():
        if pd.isna(row["4h Avg Increase"]) or pd.isna(row["2h Peak Increase"]):
            continue

        food_label = str(row["Food"])
        if len(food_label) > 20:
            food_label = food_label[:17] + "..."

        plt.annotate(
            food_label,
            xy=(row["4h Avg Increase"], row["2h Peak Increase"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            alpha=0.8,
            fontproperties=font_prop,
            weight="bold" if row["2h Peak Increase"] > 30 else "normal",
        )

    plt.title("Glucose Response Annotated by Food Item", fontsize=14, pad=15)
    plt.xlabel(f"4-Hour Average Increase ({UNIT})", fontsize=12)
    plt.ylabel(f"2-Hour Peak Increase ({UNIT})", fontsize=12)
    plt.legend()
    plt.tight_layout()

    fig_path = output_path.with_name("glucose_response_plot.png")
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    args = parse_args()
    main(args.cgm, args.food)
