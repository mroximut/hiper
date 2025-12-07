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


def register_command(cmd: Command):
    COMMAND_REGISTRY[cmd.name] = cmd


def load_builtin_commands():
    """Load all builtin commands into the registry."""
    from . import fokus, postfokus, set

    register_command(fokus.get_command())
    register_command(postfokus.get_command())
    register_command(set.get_command())
