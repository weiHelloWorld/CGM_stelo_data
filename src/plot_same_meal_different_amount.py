from pathlib import Path

import pandas as pd

from helper import setup_cjk_font
from config import COMBINED_FOOD_DATA_CSV, DOWNLOADS_DIR, EXERCISE_CSV, PROCESSED_CGM_CSV_FILE
from process_raw_food_data import get_combined_food_data
from plot_increase_for_meals_with_similar_carbs import plot_glucose_increase_for_meals


def main():
    setup_cjk_font()

    food_csv_path = Path(COMBINED_FOOD_DATA_CSV)
    if not food_csv_path.exists():
        combined_food_data = get_combined_food_data()
        food_csv_path.parent.mkdir(parents=True, exist_ok=True)
        combined_food_data.to_csv(food_csv_path, index=False)
        print(f"生成组合餐食数据: {food_csv_path}")

    food_df = pd.read_csv(food_csv_path)
    cgm_df = pd.read_csv(PROCESSED_CGM_CSV_FILE)
    exercise_df = pd.read_csv(EXERCISE_CSV)

    food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Meal_Timestamp'])
    cgm_df['Timestamp'] = pd.to_datetime(cgm_df['Timestamp'])
    exercise_df['Timestamp'] = pd.to_datetime(exercise_df['Timestamp (YYYY-MM-DDThh:mm:ss)'])

    target_meals = food_df[
        food_df['Food'].fillna('').astype(str).str.contains('宫保鸡丁', na=False)
    ].copy()
    target_meals = target_meals.sort_values('Meal_Timestamp').reset_index(drop=True)

    print(f"找到 {len(target_meals)} 个包含‘宫保鸡丁’的餐次")

    if target_meals.empty:
        print("没有找到符合条件的餐次")
        return

    output_path = DOWNLOADS_DIR / '宫保鸡丁_餐后葡萄糖增量.png'

    summary_df = plot_glucose_increase_for_meals(
        target_meals=target_meals,
        food_df=food_df,
        cgm_df=cgm_df,
        exercise_df=exercise_df,
        output_path=output_path,
    )

    print("\n=== SUMMARY ===")
    print(summary_df.to_string(index=False))


if __name__ == '__main__':
    main()
