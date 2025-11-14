import csv
import os
import datetime as dt
from typing import List, Dict, Optional

from . import config


def get_data_dir() -> str:
    """Get the data directory (from config or default)"""
    data_dir = config.get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def invalidate_cache() -> None:
    """Invalidate storage cache (e.g., after savedir change)"""
    config.invalidate_cache()


DATA_DIR = get_data_dir()

SESSIONS_CSV = os.path.join(DATA_DIR, "sessions.csv")


def _ensure_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "start", "end", "duration", "duration_formatted"])  # duration in seconds


def save_session_csv(name: str, start: dt.datetime, end: dt.datetime, duration_seconds: int) -> str:
    # Re-get data dir in case it changed
    data_dir = get_data_dir()
    sessions_csv = os.path.join(data_dir, "sessions.csv")
    _ensure_csv_header(sessions_csv)
    with open(sessions_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            name or "",
            start.isoformat(),
            end.isoformat(),
            str(duration_seconds),
            format_hms(duration_seconds),
        ])
    return sessions_csv


def format_hms(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

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
                name = row.get("name", "")
                start = dt.datetime.fromisoformat(row["start"]) if row.get("start") else None
                end = dt.datetime.fromisoformat(row["end"]) if row.get("end") else None
                duration = int(row.get("duration", "0") or 0)
            except Exception:
                continue
            if start is None or end is None:
                continue
            rows.append({
                "name": name or "",
                "start": start,
                "end": end,
                "duration": duration,
            })
    return rows


