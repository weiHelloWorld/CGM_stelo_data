import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from pathlib import Path

MG_DL_TO_MMOL_L = 1 / 18.0182

CGM_DATA_CSV_FILE_ALL = './data/Clarity_Export_Chen_Wei_2026-07-23_185008.csv'


def setup_cjk_font():
    candidates = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/mnt/c/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/msyh.ttc',
        '/mnt/c/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simhei.ttf',
    ]
    for path in candidates:
        if os.path.isfile(path):
            font_manager.fontManager.addfont(path)
            prop = FontProperties(fname=path)
            plt.rcParams['font.family'] = prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return prop

    plt.rcParams['font.sans-serif'] = [
        'Microsoft YaHei',
        'SimHei',
        'Noto Sans CJK SC',
        'Arial Unicode MS',
        'sans-serif',
    ]
    plt.rcParams['axes.unicode_minus'] = False
    return FontProperties(family=plt.rcParams['font.sans-serif'][0])


def parse_args():
    parser = argparse.ArgumentParser(description='Plot CGM hourly glucose trends.')
    parser.add_argument(
        '--cgm',
        default=CGM_DATA_CSV_FILE_ALL,
        help='Path to CGM export CSV file.',
    )
    parser.add_argument(
        '--unit',
        choices=['mg/dL', 'mmol/L'],
        default='mmol/L',
        help='Unit to display and plot glucose values.',
    )
    return parser.parse_args()


def _compute_hourly_stats(df, date_start: str, date_end: str, unit: str, offset_mgdL: float):
    df_egv = df[df['Event Type'] == 'EGV'].copy()
    # import pdb; pdb.set_trace()
    df_egv['Timestamp'] = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
    df_egv = df_egv[(df_egv['Timestamp'] >= pd.to_datetime(date_start)) & (df_egv['Timestamp'] <= pd.to_datetime(date_end))]
    print(f'Range of dates in df_egv: {df_egv["Timestamp"].min()} to {df_egv["Timestamp"].max()}')
    df_egv['Glucose Value (mg/dL)'] = pd.to_numeric(df_egv['Glucose Value (mg/dL)'], errors='coerce') + offset_mgdL
    df_egv = df_egv.dropna(subset=['Glucose Value (mg/dL)', 'Timestamp'])
    df_egv['Glucose_mmol_L'] = df_egv['Glucose Value (mg/dL)'] * MG_DL_TO_MMOL_L
    if unit == 'mmol/L':
        df_egv['Glucose'] = df_egv['Glucose_mmol_L']
    else:
        df_egv['Glucose'] = df_egv['Glucose Value (mg/dL)']
    df_egv['Date'] = df_egv['Timestamp'].dt.date
    df_egv['Hour'] = df_egv['Timestamp'].dt.hour

    hourly_stats = df_egv.groupby('Hour').agg(
        mean=('Glucose', 'mean'),
        std=('Glucose', 'std'),
    ).reset_index()

    daily_hourly_max = (
        df_egv.groupby(['Date', 'Hour'])['Glucose']
              .max()
              .reset_index()
    )
    avg_max_per_hour = (
        daily_hourly_max.groupby('Hour')['Glucose']
                        .mean()
                        .reset_index(name='avg_max_of_hourly_daily_max')
    )

    return hourly_stats.merge(avg_max_per_hour, on='Hour', how='left')


def cgm_hourly_stats_and_plot(df: pd.DataFrame, date_start_end_list: list[tuple[str, str]], unit: str, offset_mgdL_list: list[float]):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10.colors
    stems = []
    all_stats = []

    for i, (date_start, date_end) in enumerate(date_start_end_list):
        hourly_stats = _compute_hourly_stats(df, date_start=date_start, date_end=date_end, unit=unit, offset_mgdL=offset_mgdL_list[i])
        hourly_stats = hourly_stats.copy()
        hourly_stats['Date Range'] = f'{date_start} to {date_end}'
        all_stats.append(hourly_stats)

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
    ax.set_ylabel(f'葡萄糖水平 ({unit})', fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.set_xlim(0, 23)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=10)

    output_name = f'hourly_glucose_trend_{"_".join(stems)}.png'
    csv_name = f'hourly_glucose_trend_{"_".join(stems)}_{unit.replace('/', '-')}.csv'
    if all_stats:
        pd.concat(all_stats, ignore_index=True).to_csv(f'/mnt/c/Users/weich/Downloads/{csv_name}', index=False)

    plt.savefig(f'/mnt/c/Users/weich/Downloads/{output_name}', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    args = parse_args()
    setup_cjk_font()
    cgm_hourly_stats_and_plot(
        df=pd.read_csv(args.cgm),
        date_start_end_list=[
            ('2026-06-16', '2026-07-01'), 
            ('2026-07-07', '2026-07-22')],
        unit=args.unit,
        offset_mgdL_list=[-12, -7]   # offset based on fingerstick measurements, to align with CGM readings
    )
