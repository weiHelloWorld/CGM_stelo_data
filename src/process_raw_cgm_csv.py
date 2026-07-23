import pandas as pd

CGM_RAW_DATA_CSV_FILE_ALL = './data/Clarity_Export_Chen_Wei_2026-07-23_185008.csv'
PROCESSED_CGM_CSV_FILE = './data/processed_cgm_glucose_data.csv'

MG_DL_TO_MMOL_L = 1 / 18.0182
PERIOD_LIST = [
    ('2026-06-16', '2026-07-01'), 
    ('2026-07-07', '2026-07-22')
]
OFFSET_LIST = [-12, -7]  # offset based on fingerstick measurements, to align with CGM readings

def process_cgm_glucose_data(csv_path, period_list, offset_list):
    """do following:
    1. add offset to glucose values in mg/dL
    2. add glucose values in mmol/L
    """
    df = pd.read_csv(csv_path)
    df_egv_all = []
    for (date_start, date_end), offset_mgdL in zip(period_list, offset_list):
        df_egv = df[df['Event Type'] == 'EGV'].copy()
        # import pdb; pdb.set_trace()
        df_egv['Timestamp'] = pd.to_datetime(df_egv['Timestamp (YYYY-MM-DDThh:mm:ss)'])
        df_egv = df_egv[(df_egv['Timestamp'] >= pd.to_datetime(date_start)) 
                        & (df_egv['Timestamp'] <= pd.to_datetime(date_end))]
        print(f'Range of dates in df_egv: {df_egv["Timestamp"].min()} to {df_egv["Timestamp"].max()}')
        df_egv['Glucose Value (mg/dL)'] = pd.to_numeric(df_egv['Glucose Value (mg/dL)'], errors='coerce') + offset_mgdL
        df_egv['Glucose_mmol_L'] = df_egv['Glucose Value (mg/dL)'] * MG_DL_TO_MMOL_L
        df_egv_all.append(df_egv)
    df_egv_all = pd.concat(df_egv_all, ignore_index=True)
    return df_egv_all

def main():
    df_egv_all = process_cgm_glucose_data(
        CGM_RAW_DATA_CSV_FILE_ALL, period_list=PERIOD_LIST, offset_list=OFFSET_LIST)
    df_egv_all.to_csv(PROCESSED_CGM_CSV_FILE, index=False)
    print(f'Processed CGM glucose data saved to {PROCESSED_CGM_CSV_FILE}')

if __name__ == '__main__':
    main()
