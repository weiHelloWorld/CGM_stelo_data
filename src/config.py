from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
DOWNLOADS_DIR = Path("/mnt/c/Users/weich/Downloads")

COMBINED_FOOD_DATA_CSV = str(DOWNLOADS_DIR / "combined_food_data.csv")
CGM_RAW_DATA_CSV_FILE_ALL = str(DATA_DIR / "Clarity_Export_Chen_Wei_2026-07-23_185008.csv")
PROCESSED_CGM_CSV_FILE = str(DATA_DIR / "processed_cgm_glucose_data.csv")
EXERCISE_CSV = str(DATA_DIR / "exercise.csv")

MG_DL_TO_MMOL_L = 1 / 18.0182
UNIT = "mg/dL"
TEXT_LANGUAGE = "en"  # "en" or "zh"
PERIOD_LIST = [
    ("2026-06-16", "2026-07-02"),
    ("2026-07-07", "2026-07-23"),
]
OFFSET_LIST = [-12, -7]
EXCLUDE_DATES = ["2026-06-27"]

DEFAULT_CGM_CSV = PROCESSED_CGM_CSV_FILE
GLOCOSE_RESPONSE_OUTPUT_CSV = "/mnt/c/Users/weich/Downloads/glucose_response_analysis.csv"

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "OUTPUT_DIR",
    "COMBINED_FOOD_DATA_CSV",
    "CGM_RAW_DATA_CSV_FILE_ALL",
    "PROCESSED_CGM_CSV_FILE",
    "EXERCISE_CSV",
    "UNIT",
    "TEXT_LANGUAGE",
    "MG_DL_TO_MMOL_L",
    "PERIOD_LIST",
    "OFFSET_LIST",
    "EXCLUDE_DATES",
    "DEFAULT_CGM_CSV",
    "GLOCOSE_RESPONSE_OUTPUT_CSV",
]
