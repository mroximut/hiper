import argparse
import datetime as dt
import json
import os
import sys
import time
import select
import tty
import termios
from dataclasses import dataclass
from typing import Optional, Tuple

from . import Command, register_command
from .. import messages as msgs
from .. import storage


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


def _save_session_csv(name: Optional[str], start: dt.datetime, end: dt.datetime, duration_s: int) -> str:
    return storage.save_session_csv(name or "", start, end, duration_s)


def _read_line_nonblocking(timeout_s: float = 0.0) -> Optional[str]:
    rlist, _, _ = select.select([sys.stdin], [], [], timeout_s)
    if not rlist:
        return None
    line = sys.stdin.readline()
    if line is None:
        return None
    return line


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


def _tick_render(elapsed_s: int) -> None:
    msg = _elapsed_message(elapsed_s)
    timer = _format_duration(elapsed_s)
    line = f"⏱  {timer}"
    if msg:
        line += f"  —  {msg}"
    # Carriage return update without flooding lines
    print(f"\r{line}", end="", flush=True)


def _finalize_render() -> None:
    print()


def fokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--name",
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
    try:
        last_whole = -1
        while True:
            now = dt.datetime.now()
            if paused:
                elapsed = accumulated
            else:
                elapsed = accumulated + int((now - run_started).total_seconds())
            if not paused and elapsed != last_whole:
                _tick_render(elapsed)
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
        elapsed = accumulated if paused else accumulated + int((now - run_started).total_seconds())
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


register_command(
    Command(
        name="fokus",
        help="Start a focus session (live timer, save/cancel).",
        description="Start a focus session with contextual messages and a live timer.",
        configure_parser=fokus_configure_parser,
        run=fokus_run,
    )
)


