import pandas as pd
from helper import setup_cjk_font
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import re

from process_raw_food_data import COMBINED_FOOD_DATA_CSV
from process_raw_cgm_csv import PROCESSED_CGM_CSV_FILE
from English_to_Chinese_map import English_to_Chinese_map, to_Chinese_meal_name


def plot_glucose_increase_for_meals(
    target_meals,
    food_df,
    cgm_df,
    exercise_df,
    output_path,
):
    """Plot meal glucose increase and return a summary table for the target meals."""
    meal_data = []

    for idx, row in target_meals.iterrows():
        meal_time = row['Meal_Timestamp']
        meal_food = row['Food']
        meal_carbs = row['carbs']

        # --- Find pre-meal glucose: last CGM reading at or before meal time ---
        pre_meal = cgm_df[cgm_df['Timestamp'] <= meal_time]
        if len(pre_meal) == 0:
            print(f"跳过：{meal_time} 无餐前葡萄糖数据")
            continue

        pre_meal_glucose = pre_meal.iloc[-1]['Glucose_mmol_L']
        pre_meal_time = pre_meal.iloc[-1]['Timestamp']

        # --- Find post-meal glucose: readings within 0-4 hours after meal ---
        post_meal = cgm_df[
            (cgm_df['Timestamp'] > meal_time) &
            (cgm_df['Timestamp'] <= meal_time + pd.Timedelta(hours=4))
        ].copy()

        if len(post_meal) == 0:
            print(f"跳过：{meal_time} 无餐后葡萄糖数据")
            continue

        # Calculate time since meal (hours) and glucose increase from pre-meal
        post_meal['hours_since_meal'] = (
            (post_meal['Timestamp'] - meal_time).dt.total_seconds() / 3600
        )
        post_meal['glucose_increase'] = (
            post_meal['Glucose_mmol_L'] - pre_meal_glucose
        )

        meal_data.append({
            'meal_time': meal_time,
            'food': meal_food,
            'carbs': meal_carbs,
            'pre_meal_glucose': pre_meal_glucose,
            'pre_meal_time': pre_meal_time,
            'post_meal_data': post_meal[[
                'Timestamp', 'hours_since_meal',
                'glucose_increase', 'Glucose_mmol_L'
            ]].copy()
        })

    print(f"有效葡萄糖数据餐次数：{len(meal_data)}")

    if not meal_data:
        print("未生成曲线：没有有效的目标餐次数据")
        return pd.DataFrame([])

    fig, ax = plt.subplots(figsize=(14, 8))

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    markers = ['o', 's', '^', 'D', 'v', 'p']

    interruption_marker_map = {
        '运动': 'o',
        '下一餐': 's',
        '中断': 'X'
    }
    interruption_legend_added = set()

    for i, meal in enumerate(meal_data):
        data = meal['post_meal_data']
        meal_time = meal['meal_time']

        food_name_cn = to_Chinese_meal_name(meal['food'])
        short_food = food_name_cn[:40] + '...' if len(food_name_cn) > 40 else food_name_cn

        label = f"{short_food} | 碳水 = {meal['carbs']:.0f}g"

        interruption_candidates = []
        if not exercise_df.empty:
            interruption_candidates.extend(
                exercise_df.loc[
                    (exercise_df['Timestamp'] > meal_time) &
                    (exercise_df['Timestamp'] <= meal_time + pd.Timedelta(hours=4)),
                    'Timestamp'
                ].tolist()
            )
        interruption_candidates.extend(
            food_df.loc[
                (food_df['Meal_Timestamp'] > meal_time) &
                (food_df['Meal_Timestamp'] <= meal_time + pd.Timedelta(hours=4)),
                'Meal_Timestamp'
            ].tolist()
        )
        interruption_time = min(interruption_candidates) if interruption_candidates else None

        interruption_label = None
        if interruption_time is not None:
            if not exercise_df.empty and interruption_time in exercise_df['Timestamp'].values:
                interruption_label = '运动'
            elif interruption_time in food_df['Meal_Timestamp'].values:
                interruption_label = '下一餐'
            else:
                interruption_label = '中断'

            after_mask = data['Timestamp'] > interruption_time
            if after_mask.any():
                split_idx = after_mask[after_mask].index[0]
                solid_data = data.loc[:split_idx]
                dashed_data = data.loc[split_idx:]
            else:
                solid_data = data
                dashed_data = data.iloc[0:0]

            plotted_label = False

            if not solid_data.empty:
                ax.plot(
                    solid_data['hours_since_meal'],
                    solid_data['glucose_increase'],
                    color=colors[i % len(colors)],
                    linewidth=1.8,
                    alpha=0.85,
                    label=label,
                )
                plotted_label = True

            if not dashed_data.empty:
                ax.plot(
                    dashed_data['hours_since_meal'],
                    dashed_data['glucose_increase'],
                    color=colors[i % len(colors)],
                    linewidth=1.8,
                    linestyle='--',
                    alpha=0.85,
                    label=label if not plotted_label else None,
                )

                first_dashed = dashed_data.iloc[0]
                marker = interruption_marker_map.get(interruption_label, 'X')
                scatter_label = interruption_label if interruption_label not in interruption_legend_added else None
                if scatter_label is not None:
                    interruption_legend_added.add(interruption_label)

                ax.scatter(
                    first_dashed['hours_since_meal'],
                    first_dashed['glucose_increase'],
                    color=colors[i % len(colors)],
                    edgecolor='black',
                    marker=marker,
                    zorder=3,
                    s=80,
                    label=scatter_label
                )
        else:
            ax.plot(
                data['hours_since_meal'],
                data['glucose_increase'],
                color=colors[i % len(colors)],
                linewidth=1.8,
                alpha=0.85,
                label=label,
            )

    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

    ax.set_xlabel('餐后时间 (小时)', fontsize=13)
    ax.set_ylabel('餐后葡萄糖增量 (mmol/L)', fontsize=13)
    ax.set_title(
        '碳水接近血糖曲线就接近吗？餐后血糖增量',
        fontsize=20
    )
    ax.set_xlim(0, 4)
    ax.set_xticks(np.arange(0, 4.5, 0.5))
    all_handles, all_labels = ax.get_legend_handles_labels()
    meals_handles = []
    meals_labels = []
    interrupt_handles = []
    interrupt_labels = []
    for handle, label in zip(all_handles, all_labels):
        if label in interruption_marker_map:
            interrupt_handles.append(handle)
            interrupt_labels.append(label)
        else:
            meals_handles.append(handle)
            meals_labels.append(label)
    if meals_handles:
        leg1 = ax.legend(
            meals_handles,
            meals_labels,
            loc='upper right',
            bbox_to_anchor=(0.98, 0.98),
            fontsize=9,
            framealpha=0.95,
            title='餐次曲线'
        )
        ax.add_artist(leg1)
    if interrupt_handles:
        interrupt_proxies = [
            Line2D([0], [0], marker=interruption_marker_map[label], color='black', linestyle='None', markersize=8)
            for label in interrupt_labels
        ]
        ax.legend(
            interrupt_proxies,
            interrupt_labels,
            loc='lower right',
            bbox_to_anchor=(0.98, 0.58),
            fontsize=9,
            framealpha=0.95,
            title='中断类型'
        )
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    summary_rows = []
    for meal in meal_data:
        data = meal['post_meal_data']
        window_2h = data[data['hours_since_meal'].between(1.9, 2.1)]

        summary_rows.append({
            '日期': meal['meal_time'].strftime('%Y-%m-%d'),
            '时间': meal['meal_time'].strftime('%H:%M'),
            '餐名': meal['food'],
            '碳水_g': meal['carbs'],
            '餐前血糖_mmol_L': meal['pre_meal_glucose'],
            '峰值血糖_mmol_L': data['Glucose_mmol_L'].max(),
            '峰值增幅_mmol_L': data['glucose_increase'].max(),
            '达峰时间_h': data.loc[
                data['glucose_increase'].idxmax(), 'hours_since_meal'
            ],
            '2h血糖_mmol_L': window_2h['Glucose_mmol_L'].mean()
                        if len(window_2h) > 0 else np.nan,
            '2h增幅_mmol_L': window_2h['glucose_increase'].mean()
                              if len(window_2h) > 0 else np.nan,
        })

    return pd.DataFrame(summary_rows)


def main():
    setup_cjk_font()

    food_df = pd.read_csv(COMBINED_FOOD_DATA_CSV)
    cgm_df = pd.read_csv(PROCESSED_CGM_CSV_FILE)
    exercise_df = pd.read_csv('./data/exercise.csv')

    food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Meal_Timestamp'])
    cgm_df['Timestamp'] = pd.to_datetime(cgm_df['Timestamp'])
    exercise_df['Timestamp'] = pd.to_datetime(exercise_df['Timestamp (YYYY-MM-DDThh:mm:ss)'])

    target_meals = food_df[
        (food_df['carbs'] > 45) &
        (food_df['carbs'] <= 55)
    ].copy()

    print(f"找到 {len(target_meals)} 个碳水 45-55g 的餐次")

    summary_df = plot_glucose_increase_for_meals(
        target_meals=target_meals,
        food_df=food_df,
        cgm_df=cgm_df,
        exercise_df=exercise_df,
        output_path='/mnt/c/Users/weich/Downloads/glucose_increase_45_55g_carbs.png',
    )

    print("\n=== SUMMARY ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
