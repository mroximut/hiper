import argparse
import os
from typing import List

from .. import config, storage
from .. import messages as msgs
from . import Command


def set_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lang", help="Language code (e.g., en, tr)")
    p.add_argument("--nick", help="Your nickname")
    p.add_argument("--savedir", help="Directory to save sessions CSV (absolute path)")
    p.add_argument(
        "--clock",
        help="Show clock display (digital/dots/bar). "
        "To show a loading bar use format 'bar=duration', e.g. --clock bar=75m or --clock bar=1h30m"
        "Otherwise use --clock digital or --clock dots",
    )
    p.add_argument(
        "--bar-width",
        type=int,
        help="Width of the progress bar (default: 50)",
    )
    p.add_argument("--show", action="store_true", help="Show current settings")


def set_run(args: argparse.Namespace) -> int:
    if args.show:
        lang = config.get_config("lang", "en")
        nick = config.get_config("nick", "(not set)")
        savedir = config.get_data_dir()
        clock = config.get_config("clock", "dots")
        bar_width = config.get_config("bar_width", "50")

        print("Current settings:")
        print(f"  lang: {lang}")
        print(f"  nick: {nick}")
        print(f"  savedir: {savedir}")
        print(f"  clock: {clock}")
        print(f"  bar_width: {bar_width}")
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

    if updated:
        print(f"Updated: {', '.join(updated)}")
    else:
        print("No settings specified. Use --show to see current settings.")
        print("Available options: --lang, --nick, --savedir, --clock, --bar-width")

    return 0


def get_command() -> Command:
    return Command(
        name="set",
        help="Set configuration options",
        description="Set configuration options like language, "
        "nickname, save directory, etc.",
        configure_parser=set_configure_parser,
        run=set_run,
    )
