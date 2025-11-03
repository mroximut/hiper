"""hiper: A tiny, extensible terminal helper.

Run as a module during development:
  python -m hiper fokus

Or via the provided bin/hiper launcher:
  hiper fokus
"""
from .cli import main as _main

__all__ = [
    "main",
]

def main() -> None:    
    _main()


