import argparse
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class Command:
    name: str
    help: str
    description: Optional[str] = None
    configure_parser: Callable[[argparse.ArgumentParser], None] = lambda p: None
    run: Callable[[argparse.Namespace], int] = lambda args: 0


COMMAND_REGISTRY: Dict[str, Command] = {}


def register_command(cmd: Command) -> None:
    COMMAND_REGISTRY[cmd.name] = cmd


def load_builtin_commands() -> None:
    # Importing fokus registers it via side effect
    # Keep imports local to avoid import-time side effects in non-CLI contexts
    from . import fokus, postfokus, set  # noqa: F401  # pylint: disable=unused-import


