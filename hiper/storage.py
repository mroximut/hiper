import csv
import os
import datetime as dt
from typing import List, Dict, Optional


DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "hiper")
os.makedirs(DATA_DIR, exist_ok=True)

SESSIONS_CSV = os.path.join(DATA_DIR, "sessions.csv")


def _ensure_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "start", "end", "duration"])  # duration in seconds


def save_session_csv(name: str, start: dt.datetime, end: dt.datetime, duration_seconds: int) -> str:
    _ensure_csv_header(SESSIONS_CSV)
    with open(SESSIONS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            name or "",
            start.isoformat(),
            end.isoformat(),
            str(duration_seconds),
        ])
    return SESSIONS_CSV


def load_sessions_csv() -> List[Dict[str, object]]:
    if not os.path.exists(SESSIONS_CSV) or os.path.getsize(SESSIONS_CSV) == 0:
        return []
    rows: List[Dict[str, object]] = []
    with open(SESSIONS_CSV, "r", newline="", encoding="utf-8") as f:
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


