import argparse
import datetime as dt
import os
import select
import shlex
import sys
import termios
import tty
from typing import Optional

from .. import config, storage
from .. import messages as msgs
from . import Command
from .set import (
    DEFAULT_BAR_WIDTH,
    DEFAULT_CLOCK,
    DEFAULT_CLOCK_LENGTH,
    DEFAULT_COUNTDOWN,
    DEFAULT_ESTIMATE_BAR,
)


def _get_bar_width() -> int:
    # Get bar width from config (default: 42)
    try:
        bar_width = int(config.get_config("bar_width", DEFAULT_BAR_WIDTH))
        if bar_width <= 0:
            bar_width = int(DEFAULT_BAR_WIDTH)
    except (ValueError, TypeError):
        bar_width = int(DEFAULT_BAR_WIDTH)
    return bar_width


def _format_duration(seconds: int) -> str:
    return storage.format_hms(seconds)


def _save_session_csv(
    title: Optional[str], start: dt.datetime, end: dt.datetime, duration_s: int
) -> str:
    return storage.save_session_csv(title or "", start, end, duration_s)


def _handle_save(
    title: Optional[str],
    start: dt.datetime,
    end: dt.datetime,
    elapsed_s: int,
) -> None:
    """Save the session and print confirmation messages."""
    _finalize_render()
    path = _save_session_csv(title, start, end, elapsed_s)
    print(msgs.saved_session_line(_format_duration(elapsed_s)))
    print(msgs.saved_path_line(path))


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


def _restore_mode(fd, old_settings):  # type: ignore
    if fd is not None and old_settings is not None:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # type: ignore


def _print_header(start_time: dt.datetime):
    print(msgs.started_at_line(start_time))


def _tick_render(
    elapsed_s: int,
    goal_override: Optional[str] = None,
    session_title: Optional[str] = None,
    is_first_render: bool = False,
    estimate_seconds: Optional[int] = None,
    time_worked_before: Optional[int] = None,
):
    clock = config.get_config("clock", DEFAULT_CLOCK)
    if goal_override:
        clock = "bar"

    # Check if estimate bar is enabled
    estimate_bar_enabled = (
        config.get_config("estimate_bar", DEFAULT_ESTIMATE_BAR).lower() == "true"
    )
    countdown_enabled = (
        config.get_config("countdown", DEFAULT_COUNTDOWN).lower() == "true"
    )
    estimate_line = None

    # Render estimate bar if enabled and we have estimate data
    if (
        estimate_bar_enabled
        and estimate_seconds is not None
        and estimate_seconds > 0
        and time_worked_before is not None
    ):
        total_time_worked = time_worked_before + elapsed_s
        progress = total_time_worked / estimate_seconds if estimate_seconds > 0 else 1.0

        bar_width = _get_bar_width()

        # Create progress bar (capped at 100%)
        filled = min(int(progress * bar_width), bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Show percentage and time remaining/completed
        if total_time_worked >= estimate_seconds:
            # Estimate reached or exceeded
            estimate_line = (
                f":>{bar} {int(min(progress, 1.0) * 100)}% "
                f"(worked: {_format_duration(total_time_worked)})"
            )
        else:
            if countdown_enabled:
                remaining = estimate_seconds - total_time_worked
                estimate_line = (
                    f":>{bar} {int(progress * 100)}% "
                    f"(remaining: {_format_duration(remaining)})"
                )
            else:
                estimate_line = (
                    f":>{bar} {int(progress * 100)}% "
                    f"(estimate: {_format_duration(estimate_seconds)})"
                )

    # Render normal clock
    if clock == "dots":
        minutes = elapsed_s // 60
        dots = "." * minutes
        line = f":>{dots}" if dots else ":>"
    elif clock == "bar":
        # Parse target duration from goal override or clock_length config
        if goal_override:
            clock_length_str = goal_override
        else:
            clock_length_str = config.get_config("clock_length", DEFAULT_CLOCK_LENGTH)
        try:
            target_s = storage.parse_duration(clock_length_str)
        except (ValueError, TypeError) as e:
            # Fallback to 60 minutes if parsing fails
            print(f"Error: invalid clock length '{clock_length_str}': {e}")
            target_s = 3600

        # Calculate progress (can exceed 1.0 if target is exceeded)
        progress = elapsed_s / target_s if target_s > 0 else 1.0

        bar_width = _get_bar_width()

        # Create progress bar (capped at 100%)
        filled = min(int(progress * bar_width), bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Show percentage and time remaining/completed
        if elapsed_s >= target_s:
            # Target reached or exceeded
            line = (
                f":>{bar} {int(min(progress, 1.0) * 100)}% "
                f"(total: {_format_duration(elapsed_s)})"
            )
        else:
            if countdown_enabled:
                remaining = target_s - elapsed_s
                line = (
                    f":>{bar} {int(progress * 100)}% "
                    f"(remaining: {_format_duration(remaining)})"
                )
            else:
                line = f":>{bar} {int(progress * 100)}% (goal: {_format_duration(target_s)})"
    else:
        timer = _format_duration(elapsed_s)
        line = f":>{timer}"

    # Render both lines if estimate bar is shown
    if estimate_line:
        if is_first_render:
            # First render: print both lines normally
            print(f"{line}\n{estimate_line}\n", end="", flush=True)
        else:
            # Subsequent renders: move cursor up 2 lines and update both
            # Move up 2 lines, clear both lines, then print
            print(f"\033[2A\r{line}\033[K\n{estimate_line}\033[K\n", end="", flush=True)
    else:
        # No estimate bar: just render normal clock
        print(f"\r{line}", end="", flush=True)


def _finalize_render() -> None:
    """Finalize the current render line by printing a newline."""
    print()


def _parse_save_command(cmd_line: str) -> tuple[bool, Optional[str]]:
    cmd_line = cmd_line.strip()
    if not cmd_line.lower().startswith("save"):
        return False, None

    # Try to parse with shlex to handle quoted strings properly
    try:
        parts = shlex.split(cmd_line)
    except ValueError:
        # Fallback to simple split if shlex fails
        parts = cmd_line.split()

    if len(parts) == 1 and parts[0].lower() == "save":
        return True, None

    # Look for --title flag
    title = None
    for i, part in enumerate(parts):
        if part.lower() == "--title":
            if i + 1 < len(parts):
                title = parts[i + 1]
            break

    return True, title


def fokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title",
        "-t",
        help="Optional title for the session",
        default=None,
    )
    p.add_argument(
        "--goal",
        "-g",
        help="Target duration for this session (e.g., 60m, 1h30m). Overrides --clock config.",
        default=None,
    )


def fokus_run(args: argparse.Namespace) -> int:
    # Validate goal parameter if provided
    goal_override: Optional[str] = None
    if args.goal:
        try:
            # Validate the duration format
            storage.parse_duration(args.goal)
            goal_override = args.goal
        except ValueError as e:
            print(f"Error: invalid goal duration '{args.goal}': {e}")
            return 1

    start = dt.datetime.now()
    _print_header(start)

    # Load estimate data if estimate_bar is enabled and title is provided
    estimate_seconds: Optional[int] = None
    time_worked_before: Optional[int] = None
    estimate_bar_enabled = (
        config.get_config("estimate_bar", DEFAULT_ESTIMATE_BAR).lower() == "true"
    )
    if estimate_bar_enabled and args.title:
        try:
            goals = storage.load_goals_csv()
            for goal in goals:
                if goal.get("title") == args.title:
                    est_sec = goal.get("estimate_seconds", 0)
                    if isinstance(est_sec, int) and est_sec > 0:
                        estimate_seconds = est_sec
                        # Get time worked before this session
                        estimate_timestamp = goal.get("estimate_timestamp")
                        if isinstance(estimate_timestamp, dt.datetime):
                            time_worked_before = storage.get_time_worked_for_title(
                                args.title, after_timestamp=estimate_timestamp
                            )
                        else:
                            time_worked_obj = goal.get("time_worked_seconds", 0)
                            if isinstance(time_worked_obj, int):
                                time_worked_before = time_worked_obj
                            else:
                                time_worked_before = 0
                        break
        except Exception as e:
            # If loading goals fails, just continue without estimate bar
            print(f"Error: failed to load goals: {e}")

    # Running: detect space with raw mode; Paused: line input for commands
    paused = False
    accumulated = 0  # seconds accumulated before current running span
    run_started = dt.datetime.now()  # timestamp when the current running span began
    pause_started: Optional[dt.datetime] = None
    fd, old = _set_raw_mode()

    # Track if this is the first render (for estimate bar positioning)
    is_first_render = True

    # Initial render
    _tick_render(
        0,
        goal_override,
        args.title,
        is_first_render,
        estimate_seconds,
        time_worked_before,
    )
    is_first_render = False

    try:
        last_whole = -1
        while True:
            now = dt.datetime.now()
            if paused:
                elapsed = accumulated
            else:
                elapsed = accumulated + int((now - run_started).total_seconds())

            # Update display every second when running
            if not paused:
                if elapsed != last_whole:
                    _tick_render(
                        elapsed,
                        goal_override,
                        args.title,
                        is_first_render,
                        estimate_seconds,
                        time_worked_before,
                    )
                    is_first_render = False
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
                    _finalize_render()
                    _restore_mode(fd, old)
                    fd, old = None, None
                    print(msgs.paused_line(current_time=now, elapsed_seconds=elapsed))
                    continue
                else:
                    continue
            else:
                # Paused: accept command lines
                sys.stdout.write(msgs.command_prompt())
                sys.stdout.flush()
                line = sys.stdin.readline()
                cmd = (line or "").strip()

                # Handle save command (both 's' shortcut and 'save' with optional --title)
                if cmd == "s":
                    _handle_save(args.title, start, now, elapsed)
                    break

                is_save, title_override = _parse_save_command(cmd)
                if is_save:
                    # Use title from command if provided, otherwise use args.title
                    save_title = (
                        title_override if title_override is not None else args.title
                    )
                    _handle_save(save_title, start, now, elapsed)
                    break
                if cmd in ("cancel", "discard", "d"):
                    _finalize_render()
                    print(msgs.cancelled_line())
                    break
                if cmd in ("resume", "continue", "r", ""):
                    resume_now = dt.datetime.now()
                    if pause_started is not None:
                        pause_dur_s = int((resume_now - pause_started).total_seconds())
                    else:
                        pause_dur_s = 0
                    # Delete the last line
                    print("\033[1A\033[K", end="", flush=True)
                    print(msgs.resuming_line(_format_duration(pause_dur_s), resume_now))
                    fd, old = _set_raw_mode()
                    paused = False
                    run_started = resume_now
                    pause_started = None
                    last_whole = -1
                    is_first_render = True
                    _tick_render(
                        elapsed,
                        goal_override,
                        args.title,
                        is_first_render,
                        estimate_seconds,
                        time_worked_before,
                    )
                    is_first_render = False
                    continue
                # Invalid command - only save, discard/cancel, and resume/continue are allowed
                if cmd:
                    print(msgs.paused_line(current_time=now, elapsed_seconds=elapsed))
                    continue
    except KeyboardInterrupt:
        _finalize_render()
        now = dt.datetime.now()
        elapsed = (
            accumulated
            if paused
            else accumulated + int((now - run_started).total_seconds())
        )
        print(msgs.interrupted_line(elapsed_seconds=elapsed))

    finally:
        _restore_mode(fd, old)

    return 0


def get_command() -> Command:
    return Command(
        name="fokus",
        help="Start a focus session.",
        description="Start a focus session. Press Space to pause. When paused"
        " press Enter to resume, or type 'save (--title TITLE)' to save the session, "
        " or 'discard' to discard the session.",
        configure_parser=fokus_configure_parser,
        run=fokus_run,
    )
