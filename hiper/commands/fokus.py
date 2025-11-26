import argparse
import datetime as dt
import json
import os
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass
from typing import Optional, Tuple

from .. import config, storage
from .. import messages as msgs
from . import Command

DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "hiper")
os.makedirs(DATA_DIR, exist_ok=True)
SESSIONS_PATH = os.path.join(DATA_DIR, "sessions.jsonl")


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _time_of_day_message(now: dt.datetime) -> str:
    return msgs.time_of_day_message(now)


def _elapsed_message(seconds: int) -> Optional[str]:
    return msgs.elapsed_message(seconds)


def _save_session_csv(
    name: Optional[str], start: dt.datetime, end: dt.datetime, duration_s: int
) -> str:
    return storage.save_session_csv(name or "", start, end, duration_s)


def _read_key_nonblocking(timeout_s: float = 0.0) -> Optional[str]:
    rlist, _, _ = select.select([sys.stdin], [], [], timeout_s)
    if not rlist:
        return None
    ch = os.read(sys.stdin.fileno(), 1)
    if not ch:
        return None
    return ch.decode(errors="ignore")


def _set_raw_mode():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return fd, old_settings


def _restore_mode(fd, old_settings) -> None:
    if fd is not None and old_settings is not None:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _print_header(start_time: dt.datetime) -> None:
    now = dt.datetime.now()
    print(_time_of_day_message(now))
    print(msgs.instructions_line())
    print(msgs.started_at_line(start_time))
    print()


def _tick_render(elapsed_s: int, paused: bool = False) -> None:
    clock_enabled = config.get_config("clock", True)
    msg = _elapsed_message(elapsed_s)

    if not clock_enabled and not paused:
        # Show dots for each minute when clock is false and running
        minutes = elapsed_s // 60
        dots = "." * minutes
        line = f"  {dots}{minutes}" if dots else "  "
    else:
        # Show normal clock format when clock is enabled or when paused
        timer = _format_duration(elapsed_s)
        line = f"  {timer}"

    if msg:
        line += f"  —  {msg}"
    # Carriage return update without flooding lines
    print(f"\r{line}", end="", flush=True)


def _finalize_render() -> None:
    print()


def fokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title",
        help="Optional name/title for the session",
        default=None,
    )
    p.add_argument(
        "--auto-save",
        action="store_true",
        help="Automatically save on exit (Ctrl+C or 'q')",
    )


def fokus_run(args: argparse.Namespace) -> int:
    start = dt.datetime.now()
    _print_header(start)

    # Running: detect space with raw mode; Paused: line input for commands
    paused = False
    accumulated = 0  # seconds accumulated before current running span
    run_started = dt.datetime.now()  # timestamp when the current running span began
    pause_started: Optional[dt.datetime] = None
    fd, old = _set_raw_mode()
    saved = False

    # Initial render
    _tick_render(0, paused)

    try:
        last_whole = -1
        last_minute = -1
        while True:
            now = dt.datetime.now()
            if paused:
                elapsed = accumulated
            else:
                elapsed = accumulated + int((now - run_started).total_seconds())
            current_minute = elapsed // 60

            # When clock is false and running, update display every minute
            clock_enabled = config.get_config("clock", True)
            if not paused:
                if not clock_enabled:
                    # Update when minute changes
                    if current_minute != last_minute:
                        _tick_render(elapsed, paused)
                        last_minute = current_minute
                elif elapsed != last_whole:
                    # Normal behavior: update every second
                    _tick_render(elapsed, paused)
                    last_whole = elapsed
            elif paused and elapsed != last_whole:
                # # When paused, always show normal time format
                # _tick_render(elapsed, paused)
                last_whole = elapsed

            if not paused:
                key = _read_key_nonblocking(0.1)
                if key is None:
                    continue
                if key == " ":
                    # accumulate time up to this pause moment
                    accumulated += int((now - run_started).total_seconds())
                    paused = True
                    pause_started = now
                    # Render clock format one more time before pausing (if clock was false)
                    clock_enabled = config.get_config("clock", True)
                    if not clock_enabled:
                        _tick_render(accumulated, paused=True)
                    _finalize_render()
                    _restore_mode(fd, old)
                    fd, old = None, None
                    print(msgs.paused_line(current_time=now))
                    continue
                else:
                    continue
            else:
                # Paused: accept command lines
                sys.stdout.write(msgs.command_prompt())
                sys.stdout.flush()
                line = sys.stdin.readline()
                cmd = (line or "").strip().lower()
                if cmd == "save":
                    _finalize_render()
                    path = _save_session_csv(args.name, start, now, elapsed)
                    print(msgs.saved_session_line(_format_duration(elapsed)))
                    print(msgs.saved_path_line(path))
                    saved = True
                    break
                if cmd in ("cancel", "discard"):
                    _finalize_render()
                    print(msgs.cancelled_line())
                    break
                if cmd in ("resume", "continue", ""):
                    resume_now = dt.datetime.now()
                    if pause_started is not None:
                        pause_dur_s = int((resume_now - pause_started).total_seconds())
                    else:
                        pause_dur_s = 0
                    print(msgs.resuming_line(_format_duration(pause_dur_s), resume_now))
                    fd, old = _set_raw_mode()
                    paused = False
                    run_started = resume_now
                    pause_started = None
                    last_whole = -1
                    last_minute = -1
                    continue
                if cmd in ("quit", "exit", "q"):
                    _finalize_render()
                    if args.auto_save:
                        path = _save_session_csv(args.name, start, now, elapsed)
                        print(msgs.saved_session_line(_format_duration(elapsed)))
                        print(msgs.saved_path_line(path))
                        saved = True
                    else:
                        print(msgs.exited_without_saving_line())
                    break
    except KeyboardInterrupt:
        _finalize_render()
        now = dt.datetime.now()
        elapsed = (
            accumulated
            if paused
            else accumulated + int((now - run_started).total_seconds())
        )
        if args.auto_save:
            path = _save_session_csv(args.name, start, now, elapsed)
            print(msgs.saved_session_line(_format_duration(elapsed)))
            print(msgs.saved_path_line(path))
            saved = True
        else:
            print(msgs.interrupted_line())
    finally:
        _restore_mode(fd, old)

    return 0


def get_command() -> Command:
    return Command(
        name="fokus",
        help="Start a focus session (live timer, save/cancel).",
        description="Start a focus session with contextual messages and a live timer.",
        configure_parser=fokus_configure_parser,
        run=fokus_run,
    )
