
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from process_raw_cgm_csv import PERIOD_LIST, PROCESSED_CGM_CSV_FILE
from helper import setup_cjk_font

setup_cjk_font()

# Load the data
df = pd.read_csv(PROCESSED_CGM_CSV_FILE)

# Parse timestamp
df['Timestamp'] = pd.to_datetime(df['Timestamp (YYYY-MM-DDThh:mm:ss)'])
df['hour'] = df['Timestamp'].dt.hour
df['date'] = df['Timestamp'].dt.date

# Define the two periods
periods = PERIOD_LIST

period_labels = ['Period_1_Jun16_Jul01', 'Period_2_Jul07_Jul22']

results = []

for (start, end), label in zip(periods, period_labels):
    # Filter data for this period
    mask = (df['Timestamp'] >= start) & (df['Timestamp'] <= end)
    period_df = df[mask].copy()
    print(f'Processing {label}: {period_df["Timestamp"].min()} to {period_df["Timestamp"].max()}, total readings: {len(period_df)}')
    
    # Group by date and hour
    hourly_stats = period_df.groupby(['date', 'hour']).agg(
        total_readings=('Glucose Value (mg/dL)', 'count'),
        high_readings=('Glucose Value (mg/dL)', lambda x: (x > 140).sum())
    ).reset_index()
    
    # Compute ratio per hour per day
    hourly_stats['ratio'] = hourly_stats['high_readings'] / hourly_stats['total_readings']
    
    # Average ratio across all days for each hour (0-23)
    avg_ratio_by_hour = hourly_stats.groupby('hour')['ratio'].mean().reset_index()
    avg_ratio_by_hour.columns = ['hour', f'{label}_avg_ratio']
    
    # Ensure all hours 0-23 are present
    all_hours = pd.DataFrame({'hour': range(24)})
    avg_ratio_by_hour = all_hours.merge(avg_ratio_by_hour, on='hour', how='left').fillna(0)
    
    results.append(avg_ratio_by_hour)

# Merge the two period results
df_final = results[0].merge(results[1], on='hour', how='outer')
df_final = df_final.sort_values('hour').reset_index(drop=True)
df_final['hour'] = df_final['hour'].astype(int)

# Reorder columns
df_final = df_final[['hour', 
                     'Period_1_Jun16_Jul01_avg_ratio', 
                     'Period_2_Jul07_Jul22_avg_ratio']]



print(df_final.to_string(index=False))

plt.figure(figsize=(10, 6))
plt.plot(df_final['hour'], df_final['Period_1_Jun16_Jul01_avg_ratio'], marker='o', label='第1阶段：6月16日-7月1日')
plt.plot(df_final['hour'], df_final['Period_2_Jul07_Jul22_avg_ratio'], marker='o', label='第2阶段：7月7日-7月22日')
plt.title('每小时平均高血糖比例（>7.8 mmol/L）', fontsize=14)
plt.xlabel('一天中的小时', fontsize=12)
plt.ylabel('平均高血糖比例', fontsize=12)
plt.xticks(range(0, 24))
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend()
plt.tight_layout()
output_path = '/mnt/c/Users/weich/Downloads/high_glucose_ratio_by_hour.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'Saved plot to {output_path}')
