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
    try:
        from . import fokus  # noqa: F401  # pylint: disable=unused-import
    except Exception:
        # Avoid crashing CLI construction if a built-in command fails to import
        pass
    try:
        from . import postfokus  # noqa: F401  # pylint: disable=unused-import
    except Exception:
        pass


