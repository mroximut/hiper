import argparse

from .. import config, storage
from . import Command
from .fokus import fokus_run
from .set import DEFAULT_BAR_WIDTH


def read_configure_parser(p: argparse.ArgumentParser) -> None:
    subparsers = p.add_subparsers(dest="read_subcommand", help="read subcommands")

    # add subcommand
    add_parser = subparsers.add_parser("add", help="Add a new book to read.csv")
    add_parser.add_argument("--title", "-t", required=True, help="Title of the book")
    add_parser.add_argument(
        "--length", "-l", type=int, required=True, help="Total number of pages"
    )

    # update subcommand
    update_parser = subparsers.add_parser("update", help="Update reading progress")
    update_parser.add_argument("--title", "-t", required=True, help="Title of the book")
    update_group = update_parser.add_mutually_exclusive_group(required=True)
    update_group.add_argument(
        "--plus", "-p", type=int, help="Increment current_page by this amount"
    )
    update_group.add_argument(
        "--at", "-a", type=int, help="Set current_page to this value"
    )

    # Default: show progress when --title is provided (no subcommand)
    p.add_argument("--title", "-t", help="Title of the book to show progress for")


def _show_progress(title: str) -> bool:
    """Show progress bar and ask user if they want to start reading.
    Returns True if user wants to start, False otherwise.
    """
    reads = storage.load_read_csv()
    book = None
    for r in reads:
        if r.get("title") == title:
            book = r
            break

    if not book:
        print(f"Error: Book '{title}' not found in read.csv")
        return False

    length = book.get("length", 0)
    current_page = book.get("current_page", 0)

    # Ensure types are int
    if not isinstance(length, int):
        length = 0
    if not isinstance(current_page, int):
        current_page = 0

    if length == 0:
        print(f"Error: Book '{title}' has invalid length (0)")
        return False

    # Calculate percentage
    percentage = (current_page / length) * 100 if length > 0 else 0.0
    percentage = min(percentage, 100.0)

    # Create progress bar (similar to fokus command)
    bar_width = int(config.get_config("bar_width", str(DEFAULT_BAR_WIDTH)))
    filled = int((percentage / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    print(f"Progress for '{title}':")
    print(f":>{bar} {int(percentage)}% ({current_page}/{length} pages)")

    # Ask user if they want to start
    while True:
        response = input("Start reading? (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            print("Please enter 'y' or 'n'")


def read_run(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "read_subcommand", None)

    if subcommand == "add":
        title = args.title.strip()
        length = args.length

        if length <= 0:
            print(f"Error: length must be > 0, got {length}")
            return 1

        # Load existing reads
        reads = storage.load_read_csv()

        # Check if title already exists
        for r in reads:
            if r.get("title") == title:
                print(f"Error: Book '{title}' already exists in read.csv")
                return 1

        # Add new entry
        reads.append({"title": title, "length": length, "current_page": 0})
        storage.save_read_csv(reads)
        print(f"Added '{title}' with {length} pages to read.csv")
        return 0

    elif subcommand == "update":
        title = args.title.strip()

        # Load existing reads
        reads = storage.load_read_csv()

        # Find the book
        book_index = None
        for i, r in enumerate(reads):
            if r.get("title") == title:
                book_index = i
                break

        if book_index is None:
            print(f"Error: Book '{title}' not found in read.csv")
            return 1

        book = reads[book_index]
        length = book.get("length", 0)

        # Ensure length is int
        if not isinstance(length, int):
            length = 0

        if args.plus is not None:
            # Increment current_page
            current = book.get("current_page", 0)
            if not isinstance(current, int):
                current = 0
            new_page = current + args.plus
            if new_page < 0:
                new_page = 0
            if length > 0 and new_page > length:
                new_page = length
            book["current_page"] = new_page
            print(
                f"Updated '{title}': current_page = {new_page} (incremented by {args.plus})"
            )
        elif args.at is not None:
            # Set current_page
            new_page = args.at
            if new_page < 0:
                new_page = 0
            if length > 0 and new_page > length:
                new_page = length
            book["current_page"] = new_page
            print(f"Updated '{title}': current_page = {new_page}")

        reads[book_index] = book
        storage.save_read_csv(reads)
        return 0

    else:
        # Default: show progress if --title is provided
        if args.title:
            start = _show_progress(args.title)
            if start:
                # User wants to start reading - start a fokus session
                fokus_args = argparse.Namespace(title=args.title, goal=None)
                return fokus_run(fokus_args)
            return 0
        else:
            print(
                "Error: Please specify a subcommand (add, update) or use --title to show progress"
            )
            return 1


def get_command() -> Command:
    return Command(
        name="read",
        help="Manage reading list and track reading progress.",
        description="Add books, update reading progress, and view reading statistics.",
        configure_parser=read_configure_parser,
        run=read_run,
    )
