from pathlib import Path

import pandas as pd

from config import COMBINED_FOOD_DATA_CSV, DATA_DIR, EXERCISE_CSV, DOWNLOADS_DIR, MG_DL_TO_MMOL_L, UNIT
from helper import plot_glucose_increase_for_meals, setup_cjk_font
from process_raw_food_data import get_combined_food_data


CGM_CSV_PATH = DATA_DIR / "Clarity_Export_Chen_Wei_2026-07-03_145534.csv"
OUTPUT_PNG = DOWNLOADS_DIR / "selected_meal_increment_curves_july3_cgm.png"


def process_cgm_for_plot(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[df['Event Type'].astype(str).str.strip() == 'EGV'].copy()
    df['Timestamp'] = pd.to_datetime(df['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    glucose_value = pd.to_numeric(df['Glucose Value (mg/dL)'], errors='coerce')
    if UNIT == 'mmol/L':
        glucose_value = glucose_value * MG_DL_TO_MMOL_L
    df['Glucose_Value'] = glucose_value
    return df[['Timestamp', 'Glucose_Value']].dropna().sort_values('Timestamp').reset_index(drop=True)


def build_target_meals(food_df: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("imitation crab meat", ["imitation crab meat"]),
        ("zero sugar coke", ["zero sugar coke"]),
        ("eggs pocky", ["eggs", "pocky"]),
        ("Weee 半份盐水鸭 + 瑞士卷", ["盐水鸭", "瑞士卷"]),
    ]

    rows = []
    for label, terms in specs:
        food_text = food_df['Food'].fillna('').astype(str)
        candidate_mask = pd.Series(False, index=food_df.index)
        for term in terms:
            candidate_mask |= food_text.str.contains(term, case=False, na=False, regex=False)

        matches = food_df.loc[candidate_mask, ['Meal_Timestamp', 'Food', 'carbs']].copy()
        if matches.empty:
            print(f"未找到餐次: {label}")
            continue

        matches = matches.sort_values('Meal_Timestamp').reset_index(drop=True)

        exact_mask = pd.Series(True, index=matches.index)
        for term in terms:
            exact_mask &= matches['Food'].fillna('').astype(str).str.contains(term, case=False, na=False, regex=False)
        if exact_mask.any():
            chosen = matches.loc[exact_mask].iloc[0]
        else:
            chosen = matches.iloc[0]

        rows.append({
            'label': label,
            'Meal_Timestamp': chosen['Meal_Timestamp'],
            'Food': chosen['Food'],
            'carbs': chosen['carbs'],
        })

    target_meals = pd.DataFrame(rows)
    if target_meals.empty:
        raise ValueError("没有找到任何目标餐次")
    return target_meals.sort_values('Meal_Timestamp').reset_index(drop=True)


def main():
    setup_cjk_font()

    food_csv_path = Path(COMBINED_FOOD_DATA_CSV)
    if not food_csv_path.exists():
        combined_food_data = get_combined_food_data()
        food_csv_path.parent.mkdir(parents=True, exist_ok=True)
        combined_food_data.to_csv(food_csv_path, index=False)
        print(f"生成组合餐食数据: {food_csv_path}")

    food_df = pd.read_csv(food_csv_path)
    cgm_df = process_cgm_for_plot(CGM_CSV_PATH)
    exercise_df = pd.read_csv(EXERCISE_CSV)

    food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Meal_Timestamp'])
    exercise_df['Timestamp'] = pd.to_datetime(exercise_df['Timestamp (YYYY-MM-DDThh:mm:ss)'])

    target_meals = build_target_meals(food_df)
    target_meals = target_meals[
        (target_meals['Meal_Timestamp'] >= cgm_df['Timestamp'].min()) &
        (target_meals['Meal_Timestamp'] <= cgm_df['Timestamp'].max())
    ].copy()

    if target_meals.empty:
        raise ValueError("目标餐次不在 CGM 数据覆盖范围内")

    print("选中的餐次:")
    print(target_meals.to_string(index=False))

    summary_df = plot_glucose_increase_for_meals(
        target_meals=target_meals,
        food_df=food_df,
        cgm_df=cgm_df,
        exercise_df=exercise_df,
        output_path=str(OUTPUT_PNG),
        title='餐后血糖增量（相对餐前水平）',
    )


if __name__ == '__main__':
    main()
