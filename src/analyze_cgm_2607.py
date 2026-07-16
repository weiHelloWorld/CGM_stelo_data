
# %%
from bs4 import BeautifulSoup
import tqdm, sys, glob, os, time, json
import json
import numpy as np, pandas as pd

# %%
###############################################

# %%
# !pip install matplotlib

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# %%
import pandas as pd
import numpy as np

# 1. Load the Data
# Adjust filenames if they differ locally
food_df = pd.read_excel('/mnt/c/Users/weich/Dropbox/temp/others/health_data/CGM_stelo_data/data/Food_track_202607.xlsx')
cgm_df = pd.read_csv('/mnt/c/Users/weich/Downloads/Clarity_Export_Chen_Wei_2026-07-16_162558.csv') # Skip patient info rows

# 2. Clean and Parse Food Log
# Forward fill the missing dates for meals on the same day
food_df['Date'] = food_df['Date'].ffill()
# Combine Date and Time into a single datetime column
food_df['Time'] = food_df['Time'].astype(str).str.zfill(4) # Ensure HHMM format
food_df['Time'] = food_df['Time'].str[:2] + ':' + food_df['Time'].str[2:]
food_df['Meal_Timestamp'] = pd.to_datetime(food_df['Date'].astype(str) + ' ' + food_df['Time'])

# Filter out rows that don't have a valid meal description
food_df = food_df.dropna(subset=['Food']).reset_index(drop=True)

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
# output_df
# Optional: Save to a new CSV file
output_df.to_csv('/mnt/c/Users/weich/Downloads/Glucose_Meal_Analysis.csv', index=False)

# %%
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
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
font_prop = setup_cjk_font()  # seaborn theme can reset font settings

plt.figure(figsize=(12, 8))

# 1. Generate the scatter plot
sns.scatterplot(
    data=output_df, 
    x='4h Avg Increase', 
    y='2h Peak Increase',
    alpha=0.6,
    s=100, 
    color='teal',
    edgecolor='w',
    linewidth=1
)

# 2. Add the 1:1 diagonal reference line
max_val = max(output_df['4h Avg Increase'].max(), output_df['2h Peak Increase'].max())
min_val = min(output_df['4h Avg Increase'].min(), output_df['2h Peak Increase'].min())
plt.plot([min_val, max_val], [min_val, max_val], color='gray', linestyle='--', alpha=0.5, label='1:1 Reference Line')

# 3. Annotate each point with the Food name (handles both English and Chinese text)
for idx, row in output_df.iterrows():
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
import os
downloads_path = os.path.expanduser('/mnt/c/Users/weich/Downloads')
fig_path = os.path.join(downloads_path, 'glucose_response_plot.png')
plt.savefig(fig_path, dpi=300, bbox_inches='tight')


