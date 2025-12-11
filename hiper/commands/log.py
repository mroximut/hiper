import argparse
import datetime as dt

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
        ts_str = ts.isoformat()
        print(f"{ts_str} - {msg}")
    return 0


def log_run(args: argparse.Namespace) -> int:
    if args.last:
        return _print_logs_since(args.last)

    message = str(args.message or "").strip()
    if not message:
        print("Error: message cannot be empty")
        return 1

    path = storage.append_log_csv(message, dt.datetime.now())
    print(f"Logged '{message}' to {path}")
    return 0


def get_command() -> Command:
    return Command(
        name="log",
        help="Append a message or view recent logs.",
        description="Append a message with the current timestamp to log.csv, "
        "or list log entries from a recent duration with --last (e.g. 5m, 1h).",
        configure_parser=log_configure_parser,
        run=log_run,
    )
