import argparse
import datetime as dt
import subprocess
import sys
import time

from .. import config, storage
from . import Command
from .set import DEFAULT_COUNTDOWN, DEFAULT_PAUSE_END_MSG, DEFAULT_PAUSE_LENGTH


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
        print(f"Error: invalid duration '{duration_str}': {e}", file=sys.stderr)  # type: ignore[arg-type]
        return 1

    start_time = dt.datetime.now()
    end_time = start_time + dt.timedelta(seconds=duration_seconds)
    formatted_duration = storage.format_hms(duration_seconds)

    # Check if countdown is enabled
    countdown_enabled = (
        config.get_config("countdown", DEFAULT_COUNTDOWN).lower() == "true"
    )

    print(f"Pause started: {start_time.strftime('%H:%M:%S')}")
    print(f"Duration: {formatted_duration}")
    print(f"Will end at: {end_time.strftime('%H:%M:%S')}")

    # Wait for the duration with optional countdown
    try:
        if countdown_enabled:
            # Show countdown timer
            remaining_seconds = duration_seconds
            while remaining_seconds > 0:
                remaining_formatted = storage.format_hms(remaining_seconds)
                print(
                    f"\rRemaining: {remaining_formatted} (Press Ctrl+C to interrupt)",
                    end="",
                    flush=True,
                )
                time.sleep(1)
                remaining_seconds -= 1
            print()  # New line after countdown completes
        else:
            print("Waiting... Press Ctrl+C to interrupt", end="", flush=True)
            time.sleep(duration_seconds)
            print()  # New line after sleep
    except KeyboardInterrupt:
        if countdown_enabled:
            print("\nPause discarded")
        else:
            print("\nPause discarded")
        print("---------------------------------")
        return 0

    # Signal the end of the pause
    print("\nPAUSE ENDED!")
    print(f"Started at: {start_time.strftime('%H:%M:%S')}")
    print(f"Ended at: {end_time.strftime('%H:%M:%S')}")
    print(f"Duration: {formatted_duration}")

    # Use speech dispatcher for text-to-speech announcement
    print("Press Ctrl+C to stop the alarm...")

    for _ in range(10):
        # # Check if Enter was pressed (non-blocking)
        # if select.select([sys.stdin], [], [], 0)[0]:
        #     line = sys.stdin.readline()
        #     if line.strip() == "" or line.strip() == "\n":
        #         break

        # Try to announce the pause end message
        pause_end_msg = config.get_config("pause_end_msg", DEFAULT_PAUSE_END_MSG)
        # Get language for speech (use pause_lang if set, otherwise fall back to lang)
        pause_lang = config.get_config("pause_lang", "")
        if not pause_lang:
            pause_lang = config.get_config("lang", "en")

        try:
            # Use -l flag to set language for spd-say
            cmd = ["spd-say", "-l", pause_lang, pause_end_msg]
            subprocess.run(
                cmd,
                check=False,
                timeout=2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(5)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            print("Error: speech dispatcher not found", file=sys.stderr)  # type: ignore[arg-type]
            break
        except KeyboardInterrupt:
            # Clear the line to hide ^C
            print("\r\033[K", end="", flush=True)
            break

    print("---------------------------------")
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
