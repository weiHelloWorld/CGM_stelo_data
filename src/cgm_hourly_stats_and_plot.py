import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def _compute_hourly_stats(file_path):
    df = pd.read_csv(file_path)
    df_egv = df[df['Event Type'] == 'EGV'].copy()
    df_egv['Glucose Value (mg/dL)'] = pd.to_numeric(df_egv['Glucose Value (mg/dL)'], errors='coerce')
    df_egv = df_egv.dropna(subset=['Glucose Value (mg/dL)', 'Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv['Timestamp'] = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv['Hour'] = df_egv['Timestamp'].dt.hour
    return df_egv.groupby('Hour')['Glucose Value (mg/dL)'].agg(
        mean='mean',
        std='std'
    ).reset_index()


def cgm_hourly_stats_and_plot(file_path_list):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10.colors
    stems = []

    for i, file_path in enumerate(file_path_list):
        hourly_stats = _compute_hourly_stats(file_path)
        color = colors[i % len(colors)]
        label = Path(file_path).stem
        stems.append(label)

        ax.plot(
            hourly_stats['Hour'],
            hourly_stats['mean'],
            color=color,
            linewidth=2.5,
            label=f'{label} Mean'
        )
        ax.fill_between(
            hourly_stats['Hour'],
            hourly_stats['mean'] - hourly_stats['std'],
            hourly_stats['mean'] + hourly_stats['std'],
            color=color,
            alpha=0.15,
            label=f'{label} ±1 SD'
        )

    ax.set_title('Hourly Glucose Trend Over All Days', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Hour of the Day', fontsize=12)
    ax.set_ylabel('Glucose Level (mg/dL)', fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.set_xlim(0, 23)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=10)

    output_name = f'hourly_glucose_trend_{"_".join(stems)}.png'
    plt.savefig(f'/mnt/c/Users/weich/Downloads/{output_name}', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    cgm_hourly_stats_and_plot([
        "./data/Clarity_Export_Chen_Wei_2026-07-03_145534.csv",
        "/mnt/c/Users/weich/Downloads/Clarity_Export_Chen_Wei_2026-07-16_162558.csv",
    ])
