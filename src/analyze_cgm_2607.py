
# %%
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

CGM_DATA_CSV_FILE_2607 = "/mnt/c/Users/weich/Downloads/Clarity_Export_Chen_Wei_2026-07-23_021431.csv"

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
    if len(digits) == 4:
        return f"{digits[:2]}:{digits[2:]}"
    if len(digits) == 2:
        return f"{digits}:00"
    return s


def default_data_paths():
    base_dir = Path(__file__).resolve().parent
    food_path = base_dir.parent / "data" / "Food_track_202607.xlsx"
    cgm_path = Path(CGM_DATA_CSV_FILE_2607)
    return food_path, cgm_path


def default_output_path():
    downloads = Path("/mnt/c/Users/weich/Downloads")
    if not downloads.exists():
        downloads = Path("/mnt/c/Users/weich")
    return downloads / "Glucose_Meal_Analysis.csv"


# %%
# 1. Load the Data
food_path, cgm_path = default_data_paths()
food_df = pd.read_excel(food_path)
cgm_df = pd.read_csv(cgm_path)  # Skip patient info rows

# 2. Clean and Parse Food Log
# Forward fill the missing dates for meals on the same day
food_df['Date'] = food_df['Date'].ffill()
# Normalize meal times and combine into a single datetime column
food_df['Time'] = food_df['Time'].apply(normalize_meal_time)
food_df['Meal_Timestamp'] = pd.to_datetime(
    food_df['Date'].astype(str) + ' ' + food_df['Time'],
    errors='coerce'
)

# Filter out rows that don't have a valid meal description or timestamp
food_df = food_df.dropna(subset=['Food', 'Meal_Timestamp']).reset_index(drop=True)

# 3. Clean and Parse CGM Data
cgm_df = cgm_df[cgm_df['Event Type'] == 'EGV'].copy() # Keep only Estimated Glucose Values
cgm_df['Timestamp'] = pd.to_datetime(cgm_df['Timestamp (YYYY-MM-DDThh:mm:ss)'])
cgm_df['Glucose'] = pd.to_numeric(cgm_df['Glucose Value (mg/dL)'], errors='coerce')
cgm_df = cgm_df.dropna(subset=['Glucose']).sort_values('Timestamp')

# 4. Calculate Post-Meal Metrics
results = []

for idx, meal in food_df.iterrows():
    meal_time = meal['Meal_Timestamp']
    
    # Define time windows
    pre_meal_start = meal_time - pd.Timedelta(minutes=15)
    pre_meal_end = meal_time + pd.Timedelta(minutes=5)
    post_2h_end = meal_time + pd.Timedelta(hours=2)
    post_4h_end = meal_time + pd.Timedelta(hours=4)
    
    # Get Pre-meal glucose (closest reading to meal time within window)
    pre_cgm = cgm_df[(cgm_df['Timestamp'] >= pre_meal_start) & (cgm_df['Timestamp'] <= pre_meal_end)]
    if pre_cgm.empty:
        continue # Skip if no baseline glucose data is available
        
    # Take the reading closest to actual meal time
    pre_glucose = pre_cgm.iloc[(pre_cgm['Timestamp'] - meal_time).abs().argsort()[:1]]['Glucose'].values[0]
    
    # Get post-meal windows
    cgm_2h = cgm_df[(cgm_df['Timestamp'] > meal_time) & (cgm_df['Timestamp'] <= post_2h_end)]
    cgm_4h = cgm_df[(cgm_df['Timestamp'] > meal_time) & (cgm_df['Timestamp'] <= post_4h_end)]
    
    # Calculate metrics if data exists
    peak_2h_delta = (cgm_2h['Glucose'].max() - pre_glucose) if not cgm_2h.empty else np.nan
    avg_4h_delta = (cgm_4h['Glucose'].mean() - pre_glucose) if not cgm_4h.empty else np.nan
    
    results.append({
        'Date': meal['Date'],
        'Time': meal['Time'],
        'Food': meal['Food'],
        'Pre-Meal Glucose': pre_glucose,
        '2h Peak Increase': round(peak_2h_delta, 1) if pd.notna(peak_2h_delta) else np.nan,
        '4h Avg Increase': round(avg_4h_delta, 1) if pd.notna(avg_4h_delta) else np.nan
    })

# 5. Output Results
output_df = pd.DataFrame(results)
output_path = default_output_path()
output_df.to_csv(output_path, index=False)

# %%
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


def setup_cjk_font():
    """Register and activate a font that supports Chinese characters."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            font_manager.fontManager.addfont(path)
            prop = FontProperties(fname=path)
            plt.rcParams["font.family"] = prop.get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return prop
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    return FontProperties(family=plt.rcParams["font.sans-serif"][0])


font_prop = setup_cjk_font()

# Set a clean style for the plot
sns.set_theme(style="whitegrid")

plot_df = output_df.dropna(subset=['2h Peak Increase', '4h Avg Increase']).copy()
if plot_df.empty:
    print("No valid points available for plotting.")
else:
    plt.figure(figsize=(12, 8))

    # 1. Generate the scatter plot
    sns.scatterplot(
        data=plot_df, 
        x='4h Avg Increase', 
        y='2h Peak Increase',
        alpha=0.6,
        s=100, 
        color='teal',
        edgecolor='w',
        linewidth=1
    )

    # 3. Annotate each point with the Food name (handles both English and Chinese text)
    for idx, row in plot_df.iterrows():
        if pd.isna(row['4h Avg Increase']) or pd.isna(row['2h Peak Increase']):
            continue

        food_label = str(row['Food'])
        if len(food_label) > 20:
            food_label = food_label[:17] + "..."

        plt.annotate(
            food_label,
            xy=(row['4h Avg Increase'], row['2h Peak Increase']),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=9,
            alpha=0.8,
            fontproperties=font_prop,
            weight='bold' if row['2h Peak Increase'] > 30 else 'normal',
        )

    # Labels and Styling
    plt.title('Glucose Response Annotated by Food Item', fontsize=14, pad=15)
    plt.xlabel('4-Hour Average Increase (mg/dL)', fontsize=12)
    plt.ylabel('2-Hour Peak Increase (mg/dL)', fontsize=12)
    plt.legend()

    plt.tight_layout()

    # Save the figure to the Downloads folder
    fig_path = output_path.with_name('glucose_response_plot.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        
    food_label = str(row['Food'])
    if len(food_label) > 20:
        food_label = food_label[:17] + "..."
        
    plt.annotate(
        food_label,
        xy=(row['4h Avg Increase'], row['2h Peak Increase']),
        xytext=(5, 5),
        textcoords='offset points',
        fontsize=9,
        alpha=0.8,
        fontproperties=font_prop,
        weight='bold' if row['2h Peak Increase'] > 30 else 'normal',
    )

# Labels and Styling
plt.title('Glucose Response Annotated by Food Item', fontsize=14, pad=15)
plt.xlabel('4-Hour Average Increase (mg/dL)', fontsize=12)
plt.ylabel('2-Hour Peak Increase (mg/dL)', fontsize=12)
plt.legend()

plt.tight_layout()

# Save the figure to the Downloads folder
fig_path = output_path.with_name('glucose_response_plot.png')
plt.savefig(fig_path, dpi=300, bbox_inches='tight')


