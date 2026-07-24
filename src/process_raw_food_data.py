import pandas as pd
from datetime import datetime, timedelta

from config import COMBINED_FOOD_DATA_CSV, DATA_DIR

def int_to_time(t):
    if pd.isna(t):
        return None
    t = int(t)
    hour = t // 100
    minute = t % 100
    return f"{hour:02d}:{minute:02d}"

# ============================================================
# STEP 1: Read both Excel files
# ============================================================
def get_combined_food_data():
    df1 = pd.read_excel(DATA_DIR / 'Food_track_202606.xlsx')
    df2 = pd.read_excel(DATA_DIR / 'Food_track_202607.xlsx')

    # ============================================================
    # STEP 2: Clean June data
    # ============================================================
    df1_clean = df1.copy()

    # Remove duplicate header row (first row repeats column names)
    df1_clean = df1_clean[df1_clean['Meal_Timestamp'] != 'Meal_Timestamp'].reset_index(drop=True)

    # Convert Meal_Timestamp to datetime
    df1_clean['Meal_Timestamp'] = pd.to_datetime(df1_clean['Meal_Timestamp'], errors='coerce')

    # ============================================================
    # STEP 3: Clean and process July data
    # ============================================================
    df2_clean = df2.copy()

    # Remove duplicate header row
    df2_clean = df2_clean[df2_clean['Date'] != 'Date'].reset_index(drop=True)

    # Forward-fill dates: NaT rows belong to the same day as the last non-NaT row
    df2_clean['Date'] = df2_clean['Date'].ffill()

    # Convert Time from integer (e.g., 1155 = 11:55) to string format
    df2_clean['Time'] = pd.to_numeric(df2_clean['Time'], errors='coerce')

    df2_clean['Time_str'] = df2_clean['Time'].apply(int_to_time)

    # Combine Date + Time into a single Meal_Timestamp
    df2_clean['Meal_Timestamp'] = pd.to_datetime(
        df2_clean['Date'].astype(str) + ' ' + df2_clean['Time_str'],
        errors='coerce'
    )

    # ============================================================
    # STEP 4: Combine both datasets
    # ============================================================
    # Standardize columns
    cols = ['Meal_Timestamp', '餐次', 'Food', 'carbs', 'protein', 'fat', 'calories', 'activity after meal']

    df1_final = df1_clean[cols].copy()
    df2_final = df2_clean[cols].copy()

    # Concatenate and sort by timestamp
    combined = pd.concat([df1_final, df2_final], ignore_index=True)
    combined = combined.sort_values('Meal_Timestamp').reset_index(drop=True)

    # Drop rows with invalid timestamps
    combined = combined.dropna(subset=['Meal_Timestamp']).reset_index(drop=True)
    return combined


if __name__ == "__main__":
    combined_food_data = get_combined_food_data()
    combined_food_data.to_csv(COMBINED_FOOD_DATA_CSV, index=False)
