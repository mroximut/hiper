import argparse
import os
from typing import List

from .. import config
from .. import messages as msgs
from . import Command


def set_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lang", help="Language code (e.g., en, tr)")
    p.add_argument("--nick", help="Your nickname/name")
    p.add_argument("--savedir", help="Directory to save sessions CSV (absolute path)")
    p.add_argument("--clock", type=str, help="Show clock display (true/false)")
    p.add_argument("--show", action="store_true", help="Show current settings")


def set_run(args: argparse.Namespace) -> int:
    if args.show:
        # Show all current settings
        lang = config.get_config("lang", "en")
        nick = config.get_config("nick", "")
        savedir = config.get_config("savedir", "")
        clock = config.get_config("clock", True)

        print("Current settings:")
        print(f"  lang: {lang}")
        print(f"  nick: {nick or '(not set)'}")
        print(f"  savedir: {savedir or '(default)'}")
        print(f"  clock: {clock}")
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
        clock_str = args.clock.strip().lower()
        if clock_str in ("true", "false"):
            clock_value = clock_str == "true"
            config.set_config("clock", clock_value)
            updated.append(f"clock={clock_value}")
        else:
            print(f"Error: clock must be 'true' or 'false', got: {clock_str}")
            return 1

    if updated:
        print(f"Updated: {', '.join(updated)}")
    else:
        print("No settings specified. Use --show to see current settings.")
        print("Available options: --lang, --nick, --savedir, --clock")

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
