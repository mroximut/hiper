import argparse
import datetime as dt
from typing import Optional

from . import Command, register_command
from .. import storage, messages as msgs


def _parse_duration(s: str) -> int:
    s = s.strip().lower()
    if not s:
        raise ValueError("empty duration")
    total = 0
    num = ""
    unit = "m"  # default minutes if plain number
    i = 0
    has_unit = False
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
            has_unit = True
            i += 1
            continue
        raise ValueError(f"unexpected character '{ch}' in duration")
    if num:
        # trailing number with no unit -> minutes
        total += int(num) * 60
    if total <= 0:
        raise ValueError("duration must be > 0")
    return total


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
    p.add_argument("--duration", "-d", help="Duration (e.g., 25m, 1h30m, 1500s). Omit to show statistics (optionally filter by --name).")
    p.add_argument("--start", "-s", help="Start time (ISO or HH:MM). Default: infer from now - duration")
    p.add_argument("--end", "-e", help="End time (ISO or HH:MM). If omitted, infer from start + duration")
    p.add_argument("--name", "-n", help="Session name/title. With no --duration, filters statistics to this name.", default=None)


def _format_hms(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _print_statistics(name_filter: Optional[str] = None) -> int:
    rows = storage.load_sessions_csv()
    if name_filter:
        rows = [r for r in rows if (r.get("name") or "") == name_filter]
    print(msgs.stats_header(name_filter))
    if not rows:
        print(msgs.stats_line("sessions", "0"))
        return 0
    total_sessions = len(rows)
    total_seconds = sum(int(r["duration"]) for r in rows)
    now = dt.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - dt.timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    today_seconds = sum(r["duration"] for r in rows if r["start"] >= today_start)
    week_seconds = sum(r["duration"] for r in rows if r["start"] >= week_start)
    month_seconds = sum(r["duration"] for r in rows if r["start"] >= month_start)
    avg_seconds = total_seconds // total_sessions if total_sessions else 0
    print(msgs.stats_line("sessions", str(total_sessions)))
    print(msgs.stats_line("total", _format_hms(total_seconds)))
    print(msgs.stats_line("avg", _format_hms(avg_seconds)))
    print(msgs.stats_line("today", _format_hms(today_seconds)))
    print(msgs.stats_line("week", _format_hms(week_seconds)))
    print(msgs.stats_line("month", _format_hms(month_seconds)))
    return 0


def postfokus_run(args: argparse.Namespace) -> int:
    if not args.duration:
        # No duration -> show statistics, optionally filtered by name
        return _print_statistics(args.name or None)
    try:
        duration_s = _parse_duration(args.duration)
    except Exception as e:
        print(f"Invalid duration: {e}")
        return 2
    # Parse optional end first if provided
    end: Optional[dt.datetime] = None
    if args.end:
        try:
            # Reuse start parser semantics (ISO or HH:MM today)
            end = _parse_start(args.end, duration_s)
        except Exception as e:
            print(f"Invalid end: {e}")
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
        print(f"Invalid start: {e}")
        return 2
    # Infer end if not provided
    if end is None:
        end = start + dt.timedelta(seconds=duration_s)
    path = storage.save_session_csv(args.name or "", start, end, duration_s)

    print(msgs.saved_session_line(_format_hms(duration_s)))
    print(msgs.saved_path_line(path))
    return 0


register_command(
    Command(
        name="postfokus",
        help="Add a past focus session (duration, optional start/name)",
        description="Record a past focus session by providing duration and optional start time/name.",
        configure_parser=postfokus_configure_parser,
        run=postfokus_run,
    )
)


