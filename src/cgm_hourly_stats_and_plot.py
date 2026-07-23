import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

MG_DL_TO_MMOL_L = 1 / 18.0182

CGM_DATA_CSV_FILE_ALL = './data/Clarity_Export_Chen_Wei_2026-07-23_185008.csv'

def _compute_hourly_stats(df, date_start: str, date_end: str):
    df_egv = df[df['Event Type'] == 'EGV'].copy()
    # import pdb; pdb.set_trace()
    tmp_tt = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv = df_egv[(tmp_tt >= pd.to_datetime(date_start)) & (tmp_tt <= pd.to_datetime(date_end))]
    print(f'Range of dates in df_egv: {df_egv["Timestamp (YYYY-MM-DDThh:mm:ss)"].min()} to {df_egv["Timestamp (YYYY-MM-DDThh:mm:ss)"].max()}')
    df_egv['Glucose Value (mg/dL)'] = pd.to_numeric(df_egv['Glucose Value (mg/dL)'], errors='coerce')
    df_egv = df_egv.dropna(subset=['Glucose Value (mg/dL)', 'Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv['Glucose (mmol/L)'] = df_egv['Glucose Value (mg/dL)'] * MG_DL_TO_MMOL_L
    df_egv['Timestamp'] = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv['Hour'] = df_egv['Timestamp'].dt.hour
    return df_egv.groupby('Hour')['Glucose (mmol/L)'].agg(
        mean='mean',
        std='std'
    ).reset_index()


def cgm_hourly_stats_and_plot(df: pd.DataFrame, date_start_end_list: list[tuple[str, str]]):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10.colors
    stems = []

    for i, (date_start, date_end) in enumerate(date_start_end_list):
        hourly_stats = _compute_hourly_stats(df, date_start=date_start, date_end=date_end)
        color = colors[i % len(colors)]
        label = f'{date_start} to {date_end}'
        stems.append(label)

        ax.plot(
            hourly_stats['Hour'],
            hourly_stats['mean'],
            color=color,
            linewidth=2.5,
            label=f'{label}'
        )
        ax.fill_between(
            hourly_stats['Hour'],
            hourly_stats['mean'] - hourly_stats['std'],
            hourly_stats['mean'] + hourly_stats['std'],
            color=color,
            alpha=0.15,
            # label=f'{label} ±1 SD'
        )

    ax.set_title('全天分时葡萄糖变化趋势', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('一天中的小时', fontsize=12)
    ax.set_ylabel('葡萄糖水平 (mmol/L)', fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.set_xlim(0, 23)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=10)

    output_name = f'hourly_glucose_trend_{"_".join(stems)}.png'
    plt.savefig(f'/mnt/c/Users/weich/Downloads/{output_name}', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    cgm_hourly_stats_and_plot(
        df=pd.read_csv(CGM_DATA_CSV_FILE_ALL), date_start_end_list=[
            ('2026-06-16', '2026-07-01'), 
            ('2026-07-07', '2026-07-22')]
    )
        
