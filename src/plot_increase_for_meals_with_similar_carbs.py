import pandas as pd
from helper import setup_cjk_font, plot_glucose_increase_for_meals

from config import COMBINED_FOOD_DATA_CSV, EXERCISE_CSV, PROCESSED_CGM_CSV_FILE


def main():
    setup_cjk_font()

    food_df = pd.read_csv(COMBINED_FOOD_DATA_CSV)
    cgm_df = pd.read_csv(PROCESSED_CGM_CSV_FILE)
    exercise_df = pd.read_csv(EXERCISE_CSV)

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
