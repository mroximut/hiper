import csv
import datetime as dt
import os
from typing import Dict, List, Optional

from . import config


def get_data_dir() -> str:
    data_dir = config.get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


DATA_DIR = get_data_dir()

SESSIONS_CSV = os.path.join(DATA_DIR, "sessions.csv")
GOALS_CSV = os.path.join(DATA_DIR, "goals.csv")
READ_CSV = os.path.join(DATA_DIR, "read.csv")
LOG_CSV = os.path.join(DATA_DIR, "log.csv")


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

    # Update goals.csv to ensure this title has an entry and time_worked is updated
    # This ensures goals.csv stays in sync with sessions.csv
    try:
        load_goals_csv()
    except Exception as e:
        # If updating goals fails, don't fail the session save
        print(f"Error updating goals.csv: {e}")

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
            title = row.get("title", "")
            start = (
                dt.datetime.fromisoformat(row["start"]) if row.get("start") else None
            )
            end = dt.datetime.fromisoformat(row["end"]) if row.get("end") else None
            duration = int(row.get("duration", "0") or 0)
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


def _ensure_goals_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "title",
                    "estimate_seconds",
                    "estimate_formatted",
                    "estimate_timestamp",
                    "deadline",
                    "time_worked_seconds",
                    "time_worked_formatted",
                    "start_by",
                ]
            )


def load_goals_csv() -> List[Dict[str, object]]:
    """Load goals from goals.csv, ensuring all session titles have entries."""
    data_dir = get_data_dir()
    goals_csv = os.path.join(data_dir, "goals.csv")
    _ensure_goals_csv_header(goals_csv)

    # Load existing goals
    existing_goals: Dict[str, Dict[str, object]] = {}
    if os.path.exists(goals_csv) and os.path.getsize(goals_csv) > 0:
        with open(goals_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "").strip()
                if not title:
                    continue

                estimate_str = row.get("estimate_seconds", "").strip()
                estimate_seconds = int(estimate_str) if estimate_str else 0

                deadline_str = row.get("deadline", "").strip()
                deadline = (
                    dt.datetime.strptime(deadline_str, "%Y-%m-%d").date()
                    if deadline_str
                    else None
                )

                estimate_timestamp_str = row.get("estimate_timestamp", "").strip()
                estimate_timestamp = (
                    dt.datetime.fromisoformat(estimate_timestamp_str)
                    if estimate_timestamp_str
                    else None
                )

                time_worked_str = row.get("time_worked_seconds", "").strip()
                time_worked_seconds = int(time_worked_str) if time_worked_str else 0

                start_by_str = row.get("start_by", "").strip()
                start_by = (
                    dt.datetime.strptime(start_by_str, "%Y-%m-%d").date()
                    if start_by_str
                    else None
                )

                # Compute formatted values if not present (for backward compatibility)
                estimate_formatted = row.get("estimate_formatted", "").strip()
                if not estimate_formatted and estimate_seconds > 0:
                    estimate_formatted = format_hms(estimate_seconds)

                time_worked_formatted = row.get("time_worked_formatted", "").strip()
                if not time_worked_formatted and time_worked_seconds > 0:
                    time_worked_formatted = format_hms(time_worked_seconds)

                existing_goals[title] = {
                    "title": title,
                    "estimate_seconds": estimate_seconds,
                    "estimate_formatted": estimate_formatted,
                    "estimate_timestamp": estimate_timestamp,
                    "deadline": deadline,
                    "time_worked_seconds": time_worked_seconds,
                    "time_worked_formatted": time_worked_formatted,
                    "start_by": start_by,
                }

    # Get all unique titles from sessions.csv
    sessions = load_sessions_csv()
    session_titles: set[str] = set()
    for session in sessions:
        title_obj = session.get("title")
        if isinstance(title_obj, str):
            title = title_obj.strip()
            if title:
                session_titles.add(title)

    # Ensure all session titles have goal entries
    new_entries_created = False
    for title in session_titles:
        if title not in existing_goals:
            # Create entry with blank estimate/deadline/start_by
            existing_goals[title] = {
                "title": title,
                "estimate_seconds": 0,
                "estimate_formatted": "",
                "estimate_timestamp": None,
                "deadline": None,
                "time_worked_seconds": 0,
                "time_worked_formatted": "",
                "start_by": None,
            }
            new_entries_created = True

    # Update time_worked for all goals
    time_updated = False
    for goal in existing_goals.values():
        goal_title = goal.get("title")
        if isinstance(goal_title, str):
            # Get time worked after estimate timestamp if it exists
            estimate_timestamp = goal.get("estimate_timestamp")
            if isinstance(estimate_timestamp, dt.datetime):
                new_time = get_time_worked_for_title(
                    goal_title, after_timestamp=estimate_timestamp
                )
            else:
                # If no timestamp, use all time worked (backward compatibility)
                new_time = get_time_worked_for_title(goal_title)
            if goal.get("time_worked_seconds", 0) != new_time:
                goal["time_worked_seconds"] = new_time
                goal["time_worked_formatted"] = (
                    format_hms(new_time) if new_time > 0 else ""
                )
                time_updated = True
            elif not goal.get("time_worked_formatted"):
                # Ensure formatted value exists
                goal["time_worked_formatted"] = (
                    format_hms(new_time) if new_time > 0 else ""
                )

        # Ensure estimate_formatted exists
        estimate_sec = goal.get("estimate_seconds", 0)
        if isinstance(estimate_sec, int) and estimate_sec > 0:
            if not goal.get("estimate_formatted"):
                goal["estimate_formatted"] = format_hms(estimate_sec)

    # Save if new entries were created or time_worked was updated
    if new_entries_created or time_updated:
        save_goals_csv(list(existing_goals.values()))

    return list(existing_goals.values())


def save_goals_csv(goals: List[Dict[str, object]]) -> str:
    """Save goals to goals.csv."""
    data_dir = get_data_dir()
    goals_csv = os.path.join(data_dir, "goals.csv")
    _ensure_goals_csv_header(goals_csv)
    with open(goals_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "title",
                "estimate_seconds",
                "estimate_formatted",
                "estimate_timestamp",
                "deadline",
                "time_worked_seconds",
                "time_worked_formatted",
                "start_by",
            ]
        )
        for goal in goals:
            estimate_seconds = goal.get("estimate_seconds", 0)
            estimate_formatted = goal.get("estimate_formatted", "")
            if (
                not estimate_formatted
                and isinstance(estimate_seconds, int)
                and estimate_seconds > 0
            ):
                estimate_formatted = format_hms(estimate_seconds)

            estimate_timestamp = goal.get("estimate_timestamp")

            deadline = goal.get("deadline")
            time_worked_seconds = goal.get("time_worked_seconds", 0)
            time_worked_formatted = goal.get("time_worked_formatted", "")
            if (
                not time_worked_formatted
                and isinstance(time_worked_seconds, int)
                and time_worked_seconds > 0
            ):
                time_worked_formatted = format_hms(time_worked_seconds)

            start_by = goal.get("start_by")

            writer.writerow(
                [
                    goal["title"],
                    str(estimate_seconds) if estimate_seconds else "",
                    estimate_formatted,
                    estimate_timestamp.isoformat()
                    if isinstance(estimate_timestamp, dt.datetime)
                    else "",
                    deadline.strftime("%Y-%m-%d")
                    if isinstance(deadline, dt.date)
                    else "",
                    str(time_worked_seconds) if time_worked_seconds else "",
                    time_worked_formatted,
                    start_by.strftime("%Y-%m-%d")
                    if isinstance(start_by, dt.date)
                    else "",
                ]
            )
    return goals_csv


def get_time_worked_for_title(
    title: str, after_timestamp: Optional[dt.datetime] = None
) -> int:
    """Get total time worked for a given title from sessions.csv.
    If after_timestamp is provided, only counts sessions that started after that timestamp.
    """
    rows = load_sessions_csv()
    total = 0
    title_stripped = title.strip()
    for row in rows:
        row_title = row.get("title")
        if isinstance(row_title, str) and row_title.strip() == title_stripped:
            # Check if session started after timestamp
            if after_timestamp:
                start = row.get("start")
                if not isinstance(start, dt.datetime):
                    continue
                if start < after_timestamp:
                    continue

            duration = row.get("duration", 0)
            if isinstance(duration, int):
                total += duration
            elif isinstance(duration, str):
                try:
                    total += int(duration)
                except (ValueError, TypeError):
                    pass
    return total


def _ensure_read_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "length", "current_page"])


def load_read_csv() -> List[Dict[str, object]]:
    """Load reading list from read.csv."""
    data_dir = get_data_dir()
    read_csv = os.path.join(data_dir, "read.csv")
    _ensure_read_csv_header(read_csv)

    rows: List[Dict[str, object]] = []
    if not os.path.exists(read_csv) or os.path.getsize(read_csv) == 0:
        return rows

    with open(read_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            if not title:
                continue

            length_str = row.get("length", "").strip()
            length = int(length_str) if length_str else 0

            current_page_str = row.get("current_page", "").strip()
            current_page = int(current_page_str) if current_page_str else 0

            rows.append(
                {
                    "title": title,
                    "length": length,
                    "current_page": current_page,
                }
            )

    return rows


def save_read_csv(reads: List[Dict[str, object]]) -> str:
    """Save reading list to read.csv."""
    data_dir = get_data_dir()
    read_csv = os.path.join(data_dir, "read.csv")
    _ensure_read_csv_header(read_csv)

    with open(read_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "length", "current_page"])
        for read_item in reads:
            title = read_item.get("title", "")
            length = read_item.get("length", 0)
            current_page = read_item.get("current_page", 0)

            writer.writerow(
                [
                    title,
                    str(length) if length else "",
                    str(current_page) if current_page else "",
                ]
            )

    return read_csv


def _ensure_log_csv_header(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["message", "timestamp"])


def append_log_csv(message: str, when: Optional[dt.datetime] = None) -> str:
    """Append a message with timestamp to log.csv."""
    data_dir = get_data_dir()
    log_csv = os.path.join(data_dir, "log.csv")
    _ensure_log_csv_header(log_csv)
    timestamp = when or dt.datetime.now()
    with open(log_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([message, timestamp.isoformat()])
    return log_csv


def load_log_csv() -> List[Dict[str, object]]:
    """Load logs as a list of dicts."""
    data_dir = get_data_dir()
    log_csv = os.path.join(data_dir, "log.csv")
    if not os.path.exists(log_csv) or os.path.getsize(log_csv) == 0:
        return []

    rows: List[Dict[str, object]] = []
    with open(log_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            message = row.get("message", "")
            ts_str = row.get("timestamp", "")
            try:
                ts = dt.datetime.fromisoformat(ts_str) if ts_str else None
            except ValueError:
                ts = None
            rows.append({"message": message, "timestamp": ts})
    return rows
