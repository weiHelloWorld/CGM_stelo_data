from pathlib import Path
from datetime import datetime, timedelta
from bisect import bisect_left, bisect_right
import csv
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import MG_DL_TO_MMOL_L, UNIT, TEXT_LANGUAGE, DATA_DIR, DOWNLOADS_DIR
from helper import localize

SCRIPT_VERSION = "v2-resistance-1h-increment-filter-start-glucose-140"

def setup_chinese_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            from matplotlib import font_manager
            font_manager.fontManager.addfont(font_path)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=font_path).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False

def parse_dt(value):
    s = str(value or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).replace(tzinfo=None)

def parse_duration_to_min(s):
    if not s:
        return np.nan
    parts = str(s).split(":")
    try:
        if len(parts) == 3:
            h, m, sec = map(float, parts)
            return h * 60 + m + sec / 60
    except Exception:
        pass
    return np.nan

def load_clarity(path):
    cgm_times, cgm_values = [], []
    activities = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_type = row.get("Event Type", "")
            ts = parse_dt(row.get("Timestamp (YYYY-MM-DDThh:mm:ss)", ""))
            subtype = str(row.get("Event Subtype", "") or "")
            duration = row.get("Duration (hh:mm:ss)", "")
            if event_type == "EGV":
                gv = str(row.get("Glucose Value (mg/dL)", "") or "").strip()
                if ts is not None and gv:
                    try:
                        cgm_times.append(ts)
                        value = float(gv)
                        if UNIT == "mmol/L":
                            value = value * MG_DL_TO_MMOL_L
                        cgm_values.append(value)
                    except Exception:
                        pass
            elif event_type == "Activity" and ts is not None:
                activities.append({
                    "time": ts,
                    "subtype": subtype,
                    "duration": duration,
                    "duration_min": parse_duration_to_min(duration),
                })
    if not cgm_times:
        raise ValueError(localize("没有读取到 EGV 血糖数据。", "No EGV glucose data found."))
    order = np.argsort(np.array(cgm_times, dtype="datetime64[us]"))
    cgm_times = [cgm_times[i] for i in order]
    cgm_values = np.asarray(cgm_values, dtype=float)[order]
    activities.sort(key=lambda x: x["time"])
    return cgm_times, cgm_values, activities

def slice_cgm(times, values, start, end):
    lo = bisect_left(times, start)
    hi = bisect_right(times, end)
    return times[lo:hi], values[lo:hi]

def is_activity(a, activity_type):
    subtype = str(a.get("subtype", "")).strip().lower()
    return subtype == activity_type

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cgm", default=str(DATA_DIR / "Clarity_Export_Chen_Wei_2026-07-03_145534.csv"), help="Clarity CGM CSV")
    parser.add_argument("--outdir", default=str(DOWNLOADS_DIR), help=localize("输出目录", "Output directory"))
    parser.add_argument("--max-start-glucose", type=float, default=140.0, help="排除开始附近血糖大于该值的 resistance")
    parser.add_argument("--activity_type", type=str, default="resistance", help="活动类型")
    args = parser.parse_args()

    setup_chinese_font()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cgm_times, cgm_values, activities = load_clarity(args.cgm)
    acts = [a for a in activities if is_activity(a, args.activity_type)]
    if not acts:
        raise ValueError(localize(f"没有找到 Event Type=Activity 且 Event Subtype={args.activity_type} 的记录。",
                            f"No Activity records found with Event Subtype={args.activity_type}."))

    fig, ax = plt.subplots(figsize=(10, 6))
    curve_rows = []
    summary_rows = []
    excluded_rows = []

    for act in acts:
        start = act["time"]
        ts1, vals1 = slice_cgm(cgm_times, cgm_values, start, start + timedelta(hours=1))
        if len(vals1) == 0:
            excluded_rows.append({
                localize(f"{args.activity_type}开始时间", f"{args.activity_type} Start Time"): start.strftime("%Y-%m-%d %H:%M:%S"),
                localize(f"{args.activity_type}持续时间", f"{args.activity_type} Duration"): act["duration"],
                localize("排除原因", "Exclusion Reason"): localize("1h窗口无CGM数据", "No CGM data in 1h window"),
                localize("开始附近血糖", "Start Glucose"): np.nan,
            })
            continue

        baseline = float(vals1[0])
        if baseline > args.max_start_glucose:
            excluded_rows.append({
                localize(f"{args.activity_type}开始时间", f"{args.activity_type} Start Time"): start.strftime("%Y-%m-%d %H:%M:%S"),
                localize(f"{args.activity_type}持续时间", f"{args.activity_type} Duration"): act["duration"],
                localize("排除原因", "Exclusion Reason"): localize(f"开始血糖超过{args.max_start_glucose:g}", f"Start glucose exceeds {args.max_start_glucose:g}"),
                localize("开始附近血糖", "Start Glucose"): round(baseline, 1),
            })
            continue

        hours = np.array([(t - start).total_seconds() / 3600 for t in ts1], dtype=float)
        inc = np.asarray(vals1, dtype=float) - baseline
        label = f'{start.strftime("%m/%d")} {args.activity_type}, start glucose={baseline:.0f}'
        ax.plot(hours, inc, linewidth=2, label=label)

        for h, t, g, delta in zip(hours, ts1, vals1, inc):
            curve_rows.append({
                localize(f"{args.activity_type}开始时间", f"{args.activity_type} Start Time"): start.strftime("%Y-%m-%d %H:%M:%S"),
                localize(f"{args.activity_type}持续时间", f"{args.activity_type} Duration"): act["duration"],
                localize("运动后时间(h)", "Time after exercise(h)"): round(float(h), 3),
                localize("时间", "Time"): t.strftime("%Y-%m-%d %H:%M:%S"),
                localize("开始附近血糖", "Start Glucose"): round(baseline, 1),
                localize(f"原始血糖({UNIT})", f"Raw Glucose({UNIT})"): round(float(g), 1),
                localize(f"血糖增量({UNIT})", f"Glucose Increase({UNIT})"): round(float(delta), 1),
            })

        summary_rows.append({
            localize(f"{args.activity_type}开始时间", f"{args.activity_type} Start Time"): start.strftime("%Y-%m-%d %H:%M:%S"),
            localize(f"{args.activity_type}持续时间", f"{args.activity_type} Duration"): act["duration"],
            localize("1h窗口CGM点数", "CGM points in 1h window"): len(vals1),
            localize("开始附近血糖", "Start Glucose"): round(baseline, 1),
            localize("1h内最低增量", "Min increase in 1h"): round(float(np.min(inc)), 1),
            localize("1h内最高增量", "Max increase in 1h"): round(float(np.max(inc)), 1),
            localize("1h末端增量", "Increase at 1h end"): round(float(inc[-1]), 1),
            localize("1h内最低原始血糖", "Min raw glucose in 1h"): round(float(np.min(vals1)), 1),
            localize("1h内最高原始血糖", "Max raw glucose in 1h"): round(float(np.max(vals1)), 1),
        })

    ax.axhline(0, linewidth=1)
    ax.set_xlabel(localize("运动开始后时间（小时）", "Time since start(hours)"), fontsize=20)
    ax.set_ylabel(localize(f"血糖增量（{UNIT}）", f"Glucose Increase ({UNIT})"), fontsize=20)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.grid(alpha=0.3)
    if summary_rows:
        ax.legend(fontsize=9)
    fig.tight_layout()

    plot_path = outdir / f"{args.activity_type}开始后1h血糖增量曲线_排除开始超过{int(args.max_start_glucose)}.png"
    fig.savefig(plot_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    pd.DataFrame(curve_rows).to_csv(outdir / f"{args.activity_type}开始后1h血糖增量曲线_排除开始超过{int(args.max_start_glucose)}_数据.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summary_rows).to_csv(outdir / f"{args.activity_type}开始后1h血糖增量曲线_排除开始超过{int(args.max_start_glucose)}_摘要.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(excluded_rows).to_csv(outdir / f"{args.activity_type}开始后1h血糖增量曲线_排除开始超过{int(args.max_start_glucose)}_排除明细.csv", index=False, encoding="utf-8-sig")

    print(f"Script version: {SCRIPT_VERSION}")
    print(localize(f"识别到 {args.activity_type} 次数: {len(acts)}", f"Found {args.activity_type} count: {len(acts)}"))
    print(localize(f"画入图中的次数: {len(summary_rows)}", f"Plotted count: {len(summary_rows)}"))
    print(localize(f"排除次数: {len(excluded_rows)}", f"Excluded count: {len(excluded_rows)}"))
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(localize("排除明细:", "Exclusion details:"))
    print(pd.DataFrame(excluded_rows).to_string(index=False))
    print(localize("已生成:", "Generated:"))
    print(plot_path)

if __name__ == "__main__":
    main()
