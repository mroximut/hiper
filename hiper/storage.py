import csv
import datetime as dt
import os
from typing import Dict, List

from . import config


def get_data_dir() -> str:
    data_dir = config.get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def invalidate_cache() -> None:
    config.invalidate_cache()


DATA_DIR = get_data_dir()

SESSIONS_CSV = os.path.join(DATA_DIR, "sessions.csv")


def _ensure_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["title", "start", "end", "duration", "duration_formatted"]
            )  # duration in seconds


def save_session_csv(
    title: str, start: dt.datetime, end: dt.datetime, duration_seconds: int
) -> str:
    data_dir = get_data_dir()
    sessions_csv = os.path.join(data_dir, "sessions.csv")
    _ensure_csv_header(sessions_csv)
    with open(sessions_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                title or "",
                start.isoformat(),
                end.isoformat(),
                str(duration_seconds),
                format_hms(duration_seconds),
            ]
        )
    return sessions_csv


def format_hms(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
    return f"{minutes:02d}m{secs:02d}s"


def parse_duration(s: str) -> int:
    s = s.strip().lower()
    if not s:
        raise ValueError("empty duration")
    total = 0
    num = ""
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit():
            num += ch
            i += 1
            continue
        if ch in ("h", "m", "s"):
            if not num:
                raise ValueError("missing number before unit")
            val = int(num)
            if ch == "h":
                total += val * 3600
            elif ch == "m":
                total += val * 60
            else:
                total += val
            num = ""
            i += 1
            continue
        raise ValueError(f"unexpected character '{ch}' in duration")
    if num:
        # trailing number with no unit -> minutes
        total += int(num) * 60
    if total <= 0:
        raise ValueError("duration must be > 0")
    return total


def load_sessions_csv() -> List[Dict[str, object]]:
    data_dir = get_data_dir()
    sessions_csv = os.path.join(data_dir, "sessions.csv")
    if not os.path.exists(sessions_csv) or os.path.getsize(sessions_csv) == 0:
        return []
    rows: List[Dict[str, object]] = []
    with open(sessions_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                title = row.get("title", "")
                start = (
                    dt.datetime.fromisoformat(row["start"])
                    if row.get("start")
                    else None
                )
                end = dt.datetime.fromisoformat(row["end"]) if row.get("end") else None
                duration = int(row.get("duration", "0") or 0)
            except Exception:
                continue
            if start is None or end is None:
                continue
            rows.append(
                {
                    "title": title or "",
                    "start": start,
                    "end": end,
                    "duration": duration,
                }
            )
    return rows
