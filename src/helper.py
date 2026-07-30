import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import re

from config import UNIT, TEXT_LANGUAGE
from English_to_Chinese_map import convert_meal_name_language


def localize(zh_text, en_text):
    """Return text in the configured language."""
    from config import TEXT_LANGUAGE as _LANG
    return zh_text if _LANG == "zh" else en_text


def setup_cjk_font():
    candidates = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/mnt/c/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/msyh.ttc',
        '/mnt/c/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simhei.ttf',
    ]
    for path in candidates:
        if os.path.isfile(path):
            font_manager.fontManager.addfont(path)
            prop = FontProperties(fname=path)
            plt.rcParams['font.family'] = prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return prop

    plt.rcParams['font.sans-serif'] = [
        'Microsoft YaHei',
        'SimHei',
        'Noto Sans CJK SC',
        'Arial Unicode MS',
        'sans-serif',
    ]
    plt.rcParams['axes.unicode_minus'] = False
    return FontProperties(family=plt.rcParams['font.sans-serif'][0])


def plot_glucose_increase_for_meals(
    target_meals,
    food_df,
    cgm_df,
    exercise_df,
    output_path,
    title='碳水接近血糖曲线就接近吗？餐后血糖增量',
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
            print(localize(f"跳过：{meal_time} 无餐前葡萄糖数据", f"Skipping: {meal_time} no pre-meal glucose data"))
            continue

        pre_meal_glucose = pre_meal.iloc[-1]['Glucose_Value'] if 'Glucose_Value' in pre_meal.columns else pre_meal.iloc[-1]['Glucose_mmol_L']
        pre_meal_time = pre_meal.iloc[-1]['Timestamp']

        # --- Find post-meal glucose: readings within 0-4 hours after meal ---
        post_meal = cgm_df[
            (cgm_df['Timestamp'] > meal_time) &
            (cgm_df['Timestamp'] <= meal_time + pd.Timedelta(hours=4))
        ].copy()

        if len(post_meal) == 0:
            print(localize(f"跳过：{meal_time} 无餐后葡萄糖数据", f"Skipping: {meal_time} no post-meal glucose data"))
            continue

        # Calculate time since meal (hours) and glucose increase from pre-meal
        post_meal['hours_since_meal'] = (
            (post_meal['Timestamp'] - meal_time).dt.total_seconds() / 3600
        )
        glucose_col = 'Glucose_Value' if 'Glucose_Value' in post_meal.columns else 'Glucose_mmol_L'
        post_meal['glucose_increase'] = (
            post_meal[glucose_col] - pre_meal_glucose
        )

        meal_data.append({
            'meal_time': meal_time,
            'food': meal_food,
            'carbs': meal_carbs,
            'pre_meal_glucose': pre_meal_glucose,
            'pre_meal_time': pre_meal_time,
            'post_meal_data': post_meal[[
                'Timestamp', 'hours_since_meal',
                'glucose_increase', glucose_col
            ]].copy()
        })

    print(localize(f"有效葡萄糖数据餐次数：{len(meal_data)}", f"Valid meals with glucose data: {len(meal_data)}"))

    if not meal_data:
        print(localize("未生成曲线：没有有效的目标餐次数据", "No curves generated: no valid target meal data"))
        return pd.DataFrame([])

    fig, ax = plt.subplots(figsize=(14, 8))

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    markers = ['o', 's', '^', 'D', 'v', 'p']

    interruption_marker_map = {
        localize('运动', 'Exercise'): 'o',
        localize('下一餐', 'Next meal'): 's',
        localize('中断', 'Interruption'): 'X'
    }
    interruption_legend_added = set()

    for i, meal in enumerate(meal_data):
        data = meal['post_meal_data']
        meal_time = meal['meal_time']

        food_name_display = convert_meal_name_language(meal['food'])
        short_food = food_name_display[:40] + '...' if len(food_name_display) > 40 else food_name_display

        carbs_value = meal['carbs']
        if pd.isna(carbs_value):
            carbs_display = localize('未知', 'unknown')
        else:
            carbs_display = f"{carbs_value:.0f}g"

        label = f"{short_food} | {localize('碳水', 'carbs')} = {carbs_display}"

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
                interruption_label = localize('运动', 'Exercise')
            elif interruption_time in food_df['Meal_Timestamp'].values:
                interruption_label = localize('下一餐', 'Next meal')
            else:
                interruption_label = localize('中断', 'Interruption')

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

    ax.set_xlabel(localize('餐后时间 (小时)', 'Time after meal (hours)'), fontsize=13)
    ax.set_ylabel(localize(f'餐后葡萄糖增量 ({UNIT})', f'Post-meal glucose increase ({UNIT})'), fontsize=13)
    ax.set_title(
        title,
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
            title=localize('餐次曲线', 'Meal curves')
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
            title=localize('中断类型', 'Interruption type')
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

        unit_key = UNIT.replace("/", "")
        summary_rows.append({
            localize('日期', 'Date'): meal['meal_time'].strftime('%Y-%m-%d'),
            localize('时间', 'Time'): meal['meal_time'].strftime('%H:%M'),
            localize('餐名', 'Meal'): meal['food'],
            localize('碳水_g', 'Carbs_g'): meal['carbs'],
            localize(f'餐前血糖_{unit_key}', f'Pre-meal glucose_{unit_key}'): meal['pre_meal_glucose'],
            localize(f'峰值血糖_{unit_key}', f'Peak glucose_{unit_key}'): data[glucose_col].max(),
            localize(f'峰值增幅_{unit_key}', f'Peak increase_{unit_key}'): data['glucose_increase'].max(),
            localize('达峰时间_h', 'Time to peak_h'): data.loc[
                data['glucose_increase'].idxmax(), 'hours_since_meal'
            ],
            localize(f'2h血糖_{unit_key}', f'2h glucose_{unit_key}'): window_2h[glucose_col].mean()
                        if len(window_2h) > 0 else np.nan,
            localize(f'2h增幅_{unit_key}', f'2h increase_{unit_key}'): window_2h['glucose_increase'].mean()
                              if len(window_2h) > 0 else np.nan,
        })

    return pd.DataFrame(summary_rows)