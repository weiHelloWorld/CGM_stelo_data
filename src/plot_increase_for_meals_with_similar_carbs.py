import pandas as pd
from helper import setup_cjk_font, plot_glucose_increase_for_meals, compute_meal_increment_data, localize

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

    print(localize(f"找到 {len(target_meals)} 个碳水 45-55g 的餐次", f"Found {len(target_meals)} meals with 45-55g carbs"))

    # Compute one shared ylim across ALL target meals so every plot matches.
    hours_after_meal = 2.5
    all_meal_data = compute_meal_increment_data(
        target_meals, cgm_df, hours_after_meal=hours_after_meal)
    increments = pd.concat([
        meal['post_meal_data']['glucose_increase'] for meal in all_meal_data
    ])
    ymin, ymax = float(increments.min()), float(increments.max())
    pad = (ymax - ymin) * 0.05 or 1.0
    ylim = (ymin - pad, ymax + pad)

    # Output cumulative plots: plot k shows the first k meals.
    n_plots = min(5, len(target_meals))
    for k in range(1, n_plots + 1):
        subset = target_meals.head(k)
        output_path = f'/mnt/c/Users/weich/Downloads/glucose_increase_45_55g_carbs_top{k}.png'
        summary_df = plot_glucose_increase_for_meals(
            target_meals=subset,
            food_df=food_df,
            cgm_df=cgm_df,
            exercise_df=exercise_df,
            output_path=output_path,
            title=localize('碳水接近血糖曲线就接近吗？',
                           'Does similar carbs mean similar glucose curves? '),
            hours_after_meal=hours_after_meal,
            ylim=ylim,
        )

        print(f"\n=== SUMMARY (top {k}) ===")
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
