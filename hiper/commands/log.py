import argparse
import datetime as dt
from typing import Optional

from .. import storage
from . import Command


def log_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "message",
        nargs="?",
        help="Message to append to log.csv",
    )
    p.add_argument(
        "--last",
        "-l",
        help="Show logs from the last duration (e.g., 5m, 1h)",
    )
    p.add_argument(
        "--since",
        help="Show logs since this date/time (ISO datetime or YYYY-MM-DD)",
    )
    p.add_argument(
        "--until",
        help="Show logs until this date/time (ISO datetime or YYYY-MM-DD)",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Show all logs (no date filtering)",
    )
    p.add_argument(
        "--at",
        help="Specify date/time for the log entry (ISO datetime, YYYY-MM-DD, YYYY-MM-DD HH:MM, or 'yesterday')",
    )


def _format_timestamp(ts: dt.datetime) -> str:
    """Format timestamp as 'YYYY-MM-DD, HH:MM'."""
    return ts.strftime("%Y-%m-%d, %H:%M")


def _parse_datetime(date_str: str, is_until: bool = False) -> dt.datetime:
    """Parse a date/datetime string.

    Tries ISO datetime format first, then YYYY-MM-DD date format.
    For dates, --since uses start of day, --until uses end of day.
    """
    date_str = date_str.strip()

    # Try ISO datetime format first
    try:
        return dt.datetime.fromisoformat(date_str)
    except ValueError:
        pass

    # Try date format (YYYY-MM-DD)
    try:
        date_obj = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        if is_until:
            # For --until, use end of day (23:59:59.999999)
            return dt.datetime.combine(date_obj, dt.time.max)
        else:
            # For --since, use start of day (00:00:00)
            return dt.datetime.combine(date_obj, dt.time.min)
    except ValueError:
        pass

    raise ValueError(
        f"Invalid date/time format '{date_str}'. "
        "Use ISO datetime (e.g., 2024-01-15T10:30:00) or date (YYYY-MM-DD)"
    )


def _parse_at_datetime(at_str: str) -> dt.datetime:
    """Parse the --at date/time string.

    Supports:
    - ISO datetime format (e.g., 2024-01-15T10:30:00)
    - Date format YYYY-MM-DD (uses current time)
    - Date and time format YYYY-MM-DD HH:MM
    - Special case: "yesterday" (same time as now, but yesterday)
    """
    at_str = at_str.strip().lower()

    # Handle "yesterday" special case
    if at_str == "yesterday":
        now = dt.datetime.now()
        return now - dt.timedelta(days=1)

    # Try ISO datetime format first
    try:
        return dt.datetime.fromisoformat(at_str)
    except ValueError:
        pass

    # Try date and time format (YYYY-MM-DD HH:MM)
    try:
        return dt.datetime.strptime(at_str, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    # Try date format (YYYY-MM-DD) - use current time
    try:
        date_obj = dt.datetime.strptime(at_str, "%Y-%m-%d").date()
        now = dt.datetime.now()
        return dt.datetime.combine(date_obj, now.time())
    except ValueError:
        pass

    raise ValueError(
        f"Invalid --at date/time format '{at_str}'. "
        "Use ISO datetime (e.g., 2024-01-15T10:30:00), "
        "YYYY-MM-DD, YYYY-MM-DD HH:MM, or 'yesterday'"
    )


def _print_logs_today() -> int:
    """Print logs from today."""
    today = dt.date.today()
    logs = storage.load_log_csv()

    today_logs: list[tuple[dt.datetime, str]] = []
    for log in logs:
        ts = log.get("timestamp")
        if isinstance(ts, dt.datetime):
            if ts.date() == today:
                msg_obj = log.get("message", "")
                msg = str(msg_obj) if msg_obj is not None else ""
                today_logs.append((ts, msg))

    if not today_logs:
        print("No logs found for today")
        return 0

    # Sort by timestamp ascending
    today_logs.sort(key=lambda row: row[0])

    print("--------------------------------")
    for ts, msg in today_logs:
        ts_str = _format_timestamp(ts)
        print(f"{ts_str} - {msg}")
    return 0


def _print_logs_since(duration: str) -> int:
    """Print logs within the provided duration string (e.g., 5m, 1h)."""
    try:
        seconds = storage.parse_duration(duration)
    except ValueError as e:
        print(f"Error: invalid --last duration '{duration}': {e}")
        return 1

    cutoff = dt.datetime.now() - dt.timedelta(seconds=seconds)
    logs = storage.load_log_csv()

    recent: list[tuple[dt.datetime, str]] = []
    for log in logs:
        ts = log.get("timestamp")
        if isinstance(ts, dt.datetime) and ts >= cutoff:
            msg_obj = log.get("message", "")
            msg = str(msg_obj) if msg_obj is not None else ""
            recent.append((ts, msg))

    if not recent:
        print(f"No logs found in the last {duration}")
        return 0

    # Sort by timestamp ascending
    recent.sort(key=lambda row: row[0])

    for ts, msg in recent:
        ts_str = _format_timestamp(ts)
        print(f"{ts_str} - {msg}")
    return 0


def _print_logs_range(
    since: Optional[dt.datetime], until: Optional[dt.datetime]
) -> int:
    """Print logs between since and until dates (inclusive)."""
    logs = storage.load_log_csv()

    filtered: list[tuple[dt.datetime, str]] = []
    for log in logs:
        ts = log.get("timestamp")
        if not isinstance(ts, dt.datetime):
            continue

        # Apply since filter
        if since is not None and ts < since:
            continue

        # Apply until filter
        if until is not None and ts > until:
            continue

        msg_obj = log.get("message", "")
        msg = str(msg_obj) if msg_obj is not None else ""
        filtered.append((ts, msg))

    if not filtered:
        since_str = since.strftime("%Y-%m-%d %H:%M") if since else "forever"
        until_str = until.strftime("%Y-%m-%d %H:%M") if until else "now"
        print(f"No logs found between {since_str} and {until_str}")
        return 0

    # Sort by timestamp ascending
    filtered.sort(key=lambda row: row[0])

    for ts, msg in filtered:
        ts_str = _format_timestamp(ts)
        print(f"{ts_str} - {msg}")
    return 0


def log_run(args: argparse.Namespace) -> int:
    # Handle --all flag (show all logs, no filtering)
    if args.all:
        return _print_logs_range(None, None)

    # Handle --since and --until parameters
    if args.since or args.until:
        since: Optional[dt.datetime] = None
        until: Optional[dt.datetime] = None

        if args.since:
            try:
                since = _parse_datetime(args.since, is_until=False)
            except ValueError as e:
                print(f"Error: {e}")
                return 1

        if args.until:
            try:
                until = _parse_datetime(args.until, is_until=True)
            except ValueError as e:
                print(f"Error: {e}")
                return 1

        # If only --since is provided, until defaults to now
        if since and until is None:
            until = dt.datetime.now()

        # If only --until is provided, since defaults to None (forever)
        # (since is already None in this case)

        return _print_logs_range(since, until)

    # Handle --last parameter (existing behavior)
    if args.last:
        return _print_logs_since(args.last)

    message = str(args.message or "").strip()
    if not message:
        # No message and no filters: show today's logs
        return _print_logs_today()

    # Determine timestamp for the log entry
    if args.at:
        try:
            timestamp = _parse_at_datetime(args.at)
        except ValueError as e:
            print(f"Error: {e}")
            return 1
    else:
        timestamp = dt.datetime.now()

    # Append message with specified timestamp and then show today's logs
    storage.append_log_csv(message, timestamp)
    return _print_logs_today()


def get_command() -> Command:
    return Command(
        name="log",
        help="Append a message or view recent logs.",
        description="Append a message with the current timestamp to log.csv, "
        "or list log entries. Use --at to specify a date/time for the entry. "
        "Use --all to show all logs, --last for recent duration (e.g. 5m, 1h), "
        "or --since/--until to filter by date range (ISO datetime or YYYY-MM-DD).",
        configure_parser=log_configure_parser,
        run=log_run,
    )
