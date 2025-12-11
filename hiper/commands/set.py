import argparse
import os
from typing import List

from .. import config, storage
from .. import messages as msgs
from . import Command

DEFAULT_BAR_WIDTH = "42"
DEFAULT_CLOCK = "bar"
DEFAULT_CLOCK_LENGTH = "60m"
DEFAULT_ESTIMATE_BAR = "true"
DEFAULT_LANG = "en"
DEFAULT_NICK = "(not set)"
DEFAULT_WORK_PER_DAY = "8h"


def set_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lang", help="Language code")
    p.add_argument("--nick", help="Your nickname")
    p.add_argument("--savedir", help="Directory to save sessions CSV (absolute path)")
    p.add_argument(
        "--clock",
        help="To show a loading bar use format 'bar=duration', e.g. --clock bar=1h15m. "
        "Otherwise use --clock digital or --clock dots",
    )
    p.add_argument(
        "--bar-width",
        type=int,
        help="Width of the progress bar (default: 42)",
    )
    p.add_argument(
        "--estimate-bar",
        help="Show estimate progress bar in fokus sessions (true/false)",
    )
    p.add_argument(
        "--work-per-day",
        help="Workable hours per day for planning (default: 8h)",
    )
    p.add_argument("--show", action="store_true", help="Show current settings")


def set_run(args: argparse.Namespace) -> int:
    if args.show:
        lang = config.get_config("lang", DEFAULT_LANG)
        nick = config.get_config("nick", DEFAULT_NICK)
        savedir = config.get_data_dir()
        clock = config.get_config("clock", DEFAULT_CLOCK)
        bar_width = config.get_config("bar_width", DEFAULT_BAR_WIDTH)
        clock_length = config.get_config("clock_length", DEFAULT_CLOCK_LENGTH)
        estimate_bar = config.get_config("estimate_bar", DEFAULT_ESTIMATE_BAR)
        work_per_day = config.get_config("work_per_day", DEFAULT_WORK_PER_DAY)

        print("Current settings:")
        print(f"  lang: {lang}")
        print(f"  nick: {nick}")
        print(f"  savedir: {savedir}")
        print(f"  clock: {clock}")
        print(f"  bar_width: {bar_width}")
        print(f"  clock_length: {clock_length}")
        print(f"  estimate_bar: {estimate_bar}")
        print(f"  work_per_day: {work_per_day}")
        return 0

    # Set values
    updated: List[str] = []
    if args.lang is not None:
        lang = args.lang.strip().lower()
        config.set_config("lang", lang)
        msgs.set_language(lang)
        updated.append(f"lang={lang}")

    if args.nick is not None:
        nick = args.nick.strip()
        config.set_config("nick", nick)
        updated.append(f"nick={nick}")

    if args.savedir is not None:
        savedir = args.savedir.strip()
        if not os.path.isabs(savedir):
            print(f"Error: savedir must be an absolute path: {savedir}")
            return 1
        if not os.path.exists(savedir):
            try:
                os.makedirs(savedir, exist_ok=True)
            except Exception as e:
                print(f"Error: cannot create directory {savedir}: {e}")
                return 1
        config.set_config("savedir", savedir)
        updated.append(f"savedir={savedir}")

    if args.clock is not None:
        clock_parts = args.clock.strip().lower().split("=")
        clock = clock_parts[0]
        if clock not in ("digital", "dots", "bar"):
            print(f"Error: invalid clock value: {clock}")
            return 1
        config.set_config("clock", clock)
        if len(clock_parts) > 1:
            length_str = clock_parts[1]
            try:
                # Validate the duration format
                storage.parse_duration(length_str)
                config.set_config("clock_length", length_str)
                updated.append(f"clock_length={length_str}")
            except ValueError as e:
                print(f"Error: invalid clock length '{length_str}': {e}")
                return 1
        updated.append(f"clock={clock}")

    if args.bar_width is not None:
        if args.bar_width <= 0:
            print(f"Error: bar_width must be > 0: {args.bar_width}")
            return 1
        config.set_config("bar_width", str(args.bar_width))
        updated.append(f"bar_width={args.bar_width}")

    if args.estimate_bar is not None:
        estimate_bar = args.estimate_bar.strip().lower()
        if estimate_bar not in ("true", "false"):
            print(f"Error: estimate_bar must be 'true' or 'false': {estimate_bar}")
            return 1
        config.set_config("estimate_bar", estimate_bar)
        updated.append(f"estimate_bar={estimate_bar}")

    if args.work_per_day is not None:
        work_per_day = args.work_per_day.strip()
        try:
            seconds = storage.parse_duration(work_per_day)
            if seconds <= 0:
                raise ValueError("must be greater than zero")
        except Exception as e:
            print(f"Error: invalid work-per-day '{work_per_day}': {e}")
            return 1
        # Store original string so display matches user intent.
        config.set_config("work_per_day", work_per_day)
        updated.append(f"work_per_day={work_per_day}")

    if updated:
        print(f"Updated: {', '.join(updated)}")
    else:
        print("No settings specified. Use --show to see current settings.")
        print(
            "Available options: --lang, --nick, --savedir, --clock, --bar-width, "
            "--estimate-bar, --work-per-day"
        )

    return 0


def get_command() -> Command:
    return Command(
        name="set",
        help="Set configuration options.",
        description="Set configuration options like language, "
        "nickname, save directory, etc.",
        configure_parser=set_configure_parser,
        run=set_run,
    )
