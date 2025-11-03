import argparse
import sys
from typing import Callable, Dict, List, Optional
from . import messages as msgs

from .commands import COMMAND_REGISTRY, load_builtin_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hiper",
        description="hiper - a tiny, extensible terminal helper",
    )
    parser.add_argument(
        "--lang",
        help="Language code for messages (e.g., en, tr). Overrides HIPER_LANG",
        default=None,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # Ensure builtin commands are registered before building subparsers
    load_builtin_commands()

    # Dynamically add subparsers from the registry
    for command_name, command in COMMAND_REGISTRY.items():
        sub = subparsers.add_parser(
            command_name,
            help=command.help,
            description=command.description or command.help,
        )
        command.configure_parser(sub)

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available commands and exit",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    if not argv:
        # Show help with available commands
        parser.print_help()
        return 0
    args = parser.parse_args(argv)

    # Set language if provided
    if getattr(args, "lang", None):
        msgs.set_language(args.lang)

    if getattr(args, "list", False):
        print("Available commands:")
        for name in sorted(COMMAND_REGISTRY.keys()):
            print(f"  {name}")
        return 0

    cmd_name: Optional[str] = getattr(args, "command", None)
    if not cmd_name:
        parser.print_help()
        return 0

    command = COMMAND_REGISTRY.get(cmd_name)
    if not command:
        print(f"Unknown command: {cmd_name}", file=sys.stderr)
        return 2

    return command.run(args)


if __name__ == "__main__":
    raise SystemExit(main())


