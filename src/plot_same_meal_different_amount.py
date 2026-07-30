from pathlib import Path

import pandas as pd

from helper import plot_glucose_increase_for_meals, setup_cjk_font, L
from config import COMBINED_FOOD_DATA_CSV, DOWNLOADS_DIR, EXERCISE_CSV, PROCESSED_CGM_CSV_FILE
from process_raw_food_data import get_combined_food_data


def plot_for_meals_containing_keywords(keywords_list, title=None):
    setup_cjk_font()

    food_csv_path = Path(COMBINED_FOOD_DATA_CSV)
    if not food_csv_path.exists():
        combined_food_data = get_combined_food_data()
        food_csv_path.parent.mkdir(parents=True, exist_ok=True)
        combined_food_data.to_csv(food_csv_path, index=False)
        print(L(f"生成组合餐食数据: {food_csv_path}", f"Generated combined food data: {food_csv_path}"))

    food_df = pd.read_csv(food_csv_path)
    cgm_df = pd.read_csv(PROCESSED_CGM_CSV_FILE)
    exercise_df = pd.read_csv(EXERCISE_CSV)

    food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Meal_Timestamp'])
    cgm_df['Timestamp'] = pd.to_datetime(cgm_df['Timestamp'])
    exercise_df['Timestamp'] = pd.to_datetime(exercise_df['Timestamp (YYYY-MM-DDThh:mm:ss)'])

    food_name_text = food_df['Food'].fillna('').astype(str).str.lower()
    mask = pd.Series(False, index=food_df.index)
    for keyword in keywords_list:
        mask |= food_name_text.str.contains(keyword.lower(), na=False)

    target_meals = food_df[mask].copy()
    target_meals = target_meals.sort_values('Meal_Timestamp').reset_index(drop=True)

    keyword_label = '、'.join(keywords_list)
    print(L(f"找到 {len(target_meals)} 个包含'{keyword_label}'的餐次", f"Found {len(target_meals)} meals containing '{keyword_label}'"))

    if target_meals.empty:
        print(L("没有找到符合条件的餐次", "No matching meals found"))
        return

    output_path = DOWNLOADS_DIR / L(f"{keyword_label}_餐后葡萄糖增量.png", f"{keyword_label}_postprandial_glucose_increase.png")
    plot_title = title or L(f"{keyword_label}餐后血糖增量", f"{keyword_label} postprandial glucose increase")

    summary_df = plot_glucose_increase_for_meals(
        target_meals=target_meals,
        food_df=food_df,
        cgm_df=cgm_df,
        exercise_df=exercise_df,
        output_path=output_path,
        title=plot_title,
    )

    print("\n=== SUMMARY ===")
    print(summary_df.to_string(index=False))


if __name__ == '__main__':
    plot_for_meals_containing_keywords(
        ['宫保鸡丁', 'kung pao chicken'],
        title=L('宫保鸡丁餐后血糖增量', 'Kung Pao Chicken postprandial glucose increase'),
    )
    plot_for_meals_containing_keywords(
        ['辛拉面'],
        title=L('辛拉面餐后血糖增量', 'Shin Ramyun postprandial glucose increase'),
    )
