import argparse
import datetime as dt
from typing import Dict, Optional

from .. import messages as msgs
from .. import storage
from . import Command


def _parse_duration(s: str) -> int:
    return storage.parse_duration(s)


def _get_duration(row: Dict[str, object]) -> int:
    """Safely extract duration from a row dictionary."""
    duration = row.get("duration", 0)
    if isinstance(duration, int):
        return duration
    if isinstance(duration, str):
        try:
            return int(duration)
        except ValueError:
            return 0
    return 0


def _get_start(row: Dict[str, object]) -> Optional[dt.datetime]:
    """Safely extract start datetime from a row dictionary."""
    start = row.get("start")
    if isinstance(start, dt.datetime):
        return start
    return None


def _parse_start(s: Optional[str], duration_s: int) -> dt.datetime:
    if not s:
        # default: end now, infer start
        end = dt.datetime.now()
        return end - dt.timedelta(seconds=duration_s)
    s = s.strip()
    # Try ISO first
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        pass
    # Try HH:MM today
    try:
        hh, mm, *_ = s.split(":")
        now = dt.datetime.now()
        return now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    except Exception:
        pass
    raise ValueError("start must be ISO datetime or HH:MM")


def postfokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--duration",
        "-d",
        help="Duration (e.g., 25m, 1h30m, 1h30s, 1500s).",
    )
    p.add_argument(
        "--start",
        "-s",
        help="Start time (ISO or HH:MM). If omitted, inferred from now - duration",
    )
    p.add_argument(
        "--end",
        "-e",
        help="End time (ISO or HH:MM). If omitted, inferred from start + duration",
    )
    p.add_argument(
        "--title",
        "-t",
        help="Session title. With no --duration, filters statistics to this title.",
        default=None,
    )
    p.add_argument(
        "--titles",
        action="store_true",
        help="Show per-title breakdown",
    )


def _print_statistics(title_filter: Optional[str] = None) -> int:
    rows = storage.load_sessions_csv()
    if title_filter:
        rows = [r for r in rows if (r.get("title") or "") == title_filter]
    print(msgs.stats_header(title_filter))
    if not rows:
        print(msgs.stats_line("sessions", "0"))
        return 0
    total_sessions = len(rows)
    total_seconds = sum(_get_duration(r) for r in rows)
    now = dt.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - dt.timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    today_seconds = sum(
        _get_duration(r)
        for r in rows
        if (start := _get_start(r)) is not None and start >= today_start
    )
    week_seconds = sum(
        _get_duration(r)
        for r in rows
        if (start := _get_start(r)) is not None and start >= week_start
    )
    month_seconds = sum(
        _get_duration(r)
        for r in rows
        if (start := _get_start(r)) is not None and start >= month_start
    )
    avg_seconds = total_seconds // total_sessions if total_sessions else 0
    print("--------------------------------")
    print(msgs.stats_line("sessions", str(total_sessions)))
    print(msgs.stats_line("total", storage.format_hms(total_seconds)))
    print(msgs.stats_line("avg", storage.format_hms(avg_seconds)))
    print(msgs.stats_line("today", storage.format_hms(today_seconds)))
    print(msgs.stats_line("week", storage.format_hms(week_seconds)))
    print(msgs.stats_line("month", storage.format_hms(month_seconds)))
    return 0


def _print_statistics_by_title() -> int:
    rows = storage.load_sessions_csv()
    print(msgs.stats_header("by title"))
    if not rows:
        print(msgs.stats_line("sessions", "0"))
        return 0
    agg: Dict[str, Dict[str, int]] = {}
    for r in rows:
        title_str = r.get("title")
        title = str(title_str).strip() if title_str else ""
        entry = agg.setdefault(title, {"sessions": 0, "total": 0})
        entry["sessions"] += 1
        entry["total"] += _get_duration(r)
    items = sorted(agg.items(), key=lambda kv: kv[1]["total"], reverse=True)
    for title, data in items:
        label = title if title else "(unnamed)"
        print("--------------------------------")
        print(msgs.stats_line(f"{label} sessions", str(data["sessions"])))
        print(msgs.stats_line(f"{label} total", storage.format_hms(data["total"])))
    return 0


def postfokus_run(args: argparse.Namespace) -> int:
    if not args.duration:
        # No duration -> show statistics
        if args.titles and not args.title:
            return _print_statistics_by_title()
        return _print_statistics(args.title or None)
    try:
        duration_s = _parse_duration(args.duration)
    except Exception as e:
        print(msgs.invalid_X(str(e), "duration"))
        return 2
    # Parse optional end first if provided
    end: Optional[dt.datetime] = None
    if args.end:
        try:
            # Reuse start parser semantics (ISO or HH:MM today)
            end = _parse_start(args.end, duration_s)
        except Exception as e:
            print(msgs.invalid_X(str(e), "end"))
            return 2
    # Parse or infer start
    try:
        if args.start:
            start = _parse_start(args.start, duration_s)
        else:
            if end is not None:
                start = end - dt.timedelta(seconds=duration_s)
            else:
                start = _parse_start(None, duration_s)
    except Exception as e:
        print(msgs.invalid_X(str(e), "start"))
        return 2
    # Infer end if not provided
    if end is None:
        end = start + dt.timedelta(seconds=duration_s)
    path = storage.save_session_csv(args.title or "", start, end, duration_s)

    print(msgs.saved_session_line(storage.format_hms(duration_s)))
    print(msgs.saved_path_line(path))
    return 0


def get_command() -> Command:
    return Command(
        name="postfokus",
        help="Show statistics or add a past focus session (duration, optional start and title)",
        description="Record a past focus session by providing duration and optional start time and title.",
        configure_parser=postfokus_configure_parser,
        run=postfokus_run,
    )
