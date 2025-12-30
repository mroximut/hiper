import argparse
import datetime as dt
import select
import subprocess
import sys
import time

from .. import config, storage
from . import Command
from .set import DEFAULT_PAUSE_LENGTH


def pause_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--duration",
        "-d",
        help="Duration of the pause (e.g., 15m, 1h30m, 45s). "
        f"Defaults to pause_length config (default: {DEFAULT_PAUSE_LENGTH})",
    )


def pause_run(args: argparse.Namespace) -> int:
    # Get duration from argument or config
    duration_str = args.duration
    if duration_str is None:
        duration_str = config.get_config("pause_length", DEFAULT_PAUSE_LENGTH)

    try:
        duration_seconds = storage.parse_duration(duration_str)
    except ValueError as e:
        print(f"Error: invalid duration '{duration_str}': {e}", file=sys.stderr)
        return 1

    start_time = dt.datetime.now()
    end_time = start_time + dt.timedelta(seconds=duration_seconds)
    formatted_duration = storage.format_hms(duration_seconds)

    print(f"Pause started: {start_time.strftime('%H:%M:%S')}")
    print(f"Duration: {formatted_duration}")
    print(f"Will end at: {end_time.strftime('%H:%M:%S')}")
    print("Waiting...", end="", flush=True)

    # Wait for the duration
    time.sleep(duration_seconds)

    # Signal the end of the pause
    print("\n" + "=" * 50)
    print("PAUSE ENDED!")
    print(f"Started at: {start_time.strftime('%H:%M:%S')}")
    print(f"Ended at: {end_time.strftime('%H:%M:%S')}")
    print(f"Duration: {formatted_duration}")
    print("=" * 50)

    # Use speech dispatcher for text-to-speech announcement
    print("Press Enter to stop the alarm...")

    while True:
        # Check if Enter was pressed (non-blocking)
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line.strip() == "" or line.strip() == "\n":
                break

        # Try to announce "Pause ended"
        try:
            subprocess.run(
                ["spd-say", "Pause ended"],
                check=False,
                timeout=2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            print("Error: speech dispatcher not found", file=sys.stderr)
            break

        time.sleep(1)

    return 0


def get_command() -> Command:
    return Command(
        name="pause",
        help="Set a pause timer with an alarm.",
        description="Set a pause timer for a specified duration. "
        "When the pause ends, an alarm will signal the end.",
        configure_parser=pause_configure_parser,
        run=pause_run,
    )
