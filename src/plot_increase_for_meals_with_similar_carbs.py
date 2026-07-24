import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ============================================================
# 1. LOAD DATA
# ============================================================

food_df = pd.read_csv(COMBINED_FOOD_DATA_CSV)
cgm_df = pd.read_csv(PROCESSED_CGM_DATA_CSV)

# Convert timestamps to datetime
food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Meal_Timestamp'])
cgm_df['Timestamp'] = pd.to_datetime(cgm_df['Timestamp'])

# ============================================================
# 2. FILTER MEALS WITH 45–55g CARBS
# ============================================================

target_meals = food_df[
    (food_df['carbs'] >= 45) & 
    (food_df['carbs'] <= 55)
].copy()

print(f"Found {len(target_meals)} meals with carbs 45-55g")

# ============================================================
# 3. EXTRACT PRE-MEAL & POST-MEAL GLUCOSE FOR EACH MEAL
# ============================================================

meal_data = []

for idx, row in target_meals.iterrows():
    meal_time = row['Meal_Timestamp']
    meal_food = row['Food']
    meal_carbs = row['carbs']
    
    # --- Find pre-meal glucose: last CGM reading at or before meal time ---
    pre_meal = cgm_df[cgm_df['Timestamp'] <= meal_time]
    if len(pre_meal) == 0:
        print(f"SKIP: No pre-meal glucose for {meal_time}")
        continue
    
    pre_meal_glucose = pre_meal.iloc[-1]['Glucose Value (mg/dL)']
    pre_meal_time = pre_meal.iloc[-1]['Timestamp']
    
    # --- Find post-meal glucose: readings within 0-4 hours after meal ---
    post_meal = cgm_df[
        (cgm_df['Timestamp'] > meal_time) & 
        (cgm_df['Timestamp'] <= meal_time + pd.Timedelta(hours=4))
    ].copy()
    
    if len(post_meal) == 0:
        print(f"SKIP: No post-meal glucose for {meal_time}")
        continue
    
    # Calculate time since meal (hours) and glucose increase from pre-meal
    post_meal['hours_since_meal'] = (
        (post_meal['Timestamp'] - meal_time).dt.total_seconds() / 3600
    )
    post_meal['glucose_increase'] = (
        post_meal['Glucose Value (mg/dL)'] - pre_meal_glucose
    )
    
    meal_data.append({
        'meal_time': meal_time,
        'food': meal_food,
        'carbs': meal_carbs,
        'pre_meal_glucose': pre_meal_glucose,
        'pre_meal_time': pre_meal_time,
        'post_meal_data': post_meal[[
            'Timestamp', 'hours_since_meal', 
            'glucose_increase', 'Glucose Value (mg/dL)'
        ]].copy()
    })

print(f"Meals with valid glucose data: {len(meal_data)}")

# ============================================================
# 4. PLOT: GLUCOSE INCREASE vs TIME SINCE MEAL
# ============================================================

fig, ax = plt.subplots(figsize=(14, 8))

colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
markers = ['o', 's', '^', 'D', 'v', 'p']

for i, meal in enumerate(meal_data):
    data = meal['post_meal_data']
    
    # Shorten label for legend readability
    short_food = meal['food'][:40] + '...' if len(meal['food']) > 40 else meal['food']
    label = f"{meal['meal_time'].strftime('%m-%d %H:%M')} | {short_food} | {meal['carbs']:.0f}g"
    
    ax.plot(
        data['hours_since_meal'], 
        data['glucose_increase'], 
        color=colors[i % len(colors)], 
        marker=markers[i % len(markers)], 
        markersize=3.5, 
        linewidth=1.8, 
        alpha=0.85, 
        label=label,
        markevery=3  # show marker every 3rd point to reduce clutter
    )

# Reference line at zero (pre-meal baseline)
ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

# Formatting
ax.set_xlabel('Time Since Meal (hours)', fontsize=13)
ax.set_ylabel('Glucose Increase from Pre-meal (mg/dL)', fontsize=13)
ax.set_title(
    'Post-Meal Glucose Response\n(Meals with 45–55g Carbohydrates, 0–4 hours)', 
    fontsize=15
)
ax.set_xlim(0, 4)
ax.set_xticks(np.arange(0, 4.5, 0.5))
ax.legend(
    loc='upper left', 
    bbox_to_anchor=(1.02, 1), 
    fontsize=9, 
    framealpha=0.95
)
ax.grid(True, alpha=0.3, linestyle='-')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('glucose_increase_45_55g_carbs.png', dpi=150, bbox_inches='tight')
plt.show()

# ============================================================
# 5. SUMMARY TABLE
# ============================================================

summary_rows = []
for meal in meal_data:
    data = meal['post_meal_data']
    
    # Find 2-hour window (1.9–2.1h)
    window_2h = data[data['hours_since_meal'].between(1.9, 2.1)]
    
    summary_rows.append({
        'Date': meal['meal_time'].strftime('%Y-%m-%d'),
        'Time': meal['meal_time'].strftime('%H:%M'),
        'Meal': meal['food'],
        'Carbs_g': meal['carbs'],
        'Pre_meal_BG': meal['pre_meal_glucose'],
        'Peak_BG': data['Glucose Value (mg/dL)'].max(),
        'Peak_Increase_mg_dL': data['glucose_increase'].max(),
        'Time_to_Peak_h': data.loc[
            data['glucose_increase'].idxmax(), 'hours_since_meal'
        ],
        'BG_at_2h': window_2h['Glucose Value (mg/dL)'].mean() 
                    if len(window_2h) > 0 else np.nan,
        'Increase_at_2h': window_2h['glucose_increase'].mean() 
                          if len(window_2h) > 0 else np.nan,
    })

summary_df = pd.DataFrame(summary_rows)
print("\n=== SUMMARY ===")
print(summary_df.to_string(index=False))

# summary_df.to_csv('meal_summary_45_55g_carbs.csv', index=False)
