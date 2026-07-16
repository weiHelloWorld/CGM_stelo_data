import pandas as pd
import matplotlib.pyplot as plt


def cgm_hourly_stats_and_plot(file_path):
    # 1. Load the exported CSV data file
    df = pd.read_csv(file_path)

    # 2. Filter for EGV (Estimated Glucose Value) events and convert glucose levels to numeric
    df_egv = df[df['Event Type'] == 'EGV'].copy()
    df_egv['Glucose Value (mg/dL)'] = pd.to_numeric(df_egv['Glucose Value (mg/dL)'], errors='coerce')

    # 3. Clean missing values from critical columns
    df_egv = df_egv.dropna(subset=['Glucose Value (mg/dL)', 'Timestamp (YYYY-MM-DDThh:mm:ss)'])

    # 4. Parse the timestamp column and extract the hour of the day (0-23)
    df_egv['Timestamp'] = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv['Hour'] = df_egv['Timestamp'].dt.hour

    # 5. Group by 'Hour' and compute the mean, median, 25th percentile, and 75th percentile
    hourly_stats = df_egv.groupby('Hour')['Glucose Value (mg/dL)'].agg(
        mean='mean',
        median='median',
        quantile_25=lambda x: x.quantile(0.25),
        quantile_75=lambda x: x.quantile(0.75)
    ).reset_index()

    # 6. Initialize the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the mean glucose level as a solid line
    ax.plot(
        hourly_stats['Hour'],
        hourly_stats['mean'],
        color='#1f77b4',
        linewidth=2.5,
        label='Mean Glucose'
    )

    # Plot the median glucose level as a dashed line for reference
    ax.plot(
        hourly_stats['Hour'],
        hourly_stats['median'],
        color='#1f77b4',
        linestyle='--',
        linewidth=1.5,
        alpha=0.8,
        label='Median Glucose'
    )

    # Fill/shade the region between the 25th and 75th percentiles (Interquartile Range)
    ax.fill_between(
        hourly_stats['Hour'],
        hourly_stats['quantile_25'],
        hourly_stats['quantile_75'],
        color='#1f77b4',
        alpha=0.15,
        label='Interquartile Range (25th - 75th %ile)'
    )

    # 7. Customize axis labels, limits, ticks, and title
    ax.set_title('Hourly Glucose Trend Over All Days', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Hour of the Day', fontsize=12)
    ax.set_ylabel('Glucose Level (mg/dL)', fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.set_xlim(0, 23)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=10)

    # Save the plot securely to your environment
    plt.savefig(f'/mnt/Data/weich/Downloads/hourly_glucose_trend_{file_path.split("/")[-1].split(".")[0]}.png', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    cgm_hourly_stats_and_plot("Clarity_Export_Chen_Wei_2026-07-16_162558.csv")
