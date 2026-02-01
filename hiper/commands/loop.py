import argparse
import datetime as dt
from typing import Dict, List, Optional, Set

from .. import storage
from . import Command


def _parse_frequency(frequency: str) -> Set[str]:
    """Parse frequency string and return set of day abbreviations.
    'daily' returns all days, otherwise parses comma-separated days like 'mon,tue,sat'.
    """
    freq = frequency.strip().lower()
    if freq == "daily":
        return {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

    # Parse comma-separated days
    days: Set[str] = set()
    day_map: Dict[str, str] = {
        "mon": "mon",
        "monday": "mon",
        "tue": "tue",
        "tuesday": "tue",
        "wed": "wed",
        "wednesday": "wed",
        "thu": "thu",
        "thursday": "thu",
        "fri": "fri",
        "friday": "fri",
        "sat": "sat",
        "saturday": "sat",
        "sun": "sun",
        "sunday": "sun",
    }

    for day_str in freq.split(","):
        day_str = day_str.strip().lower()
        if day_str in day_map:
            days.add(day_map[day_str])

    return days


def _get_today_day_abbr() -> str:
    """Get today's day abbreviation (mon, tue, wed, etc.)."""
    today = dt.date.today()
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return day_names[today.weekday()]


def _get_day_abbr_for_date(date: dt.date) -> str:
    """Get day abbreviation for a given date (mon, tue, wed, etc.)."""
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return day_names[date.weekday()]


def _is_habit_scheduled_today(frequency: str) -> bool:
    """Check if a habit is scheduled for today based on its frequency."""
    scheduled_days = _parse_frequency(frequency)
    today_abbr = _get_today_day_abbr()
    return today_abbr in scheduled_days


def _check_habit_match(log_message: str, habit_name: str) -> Optional[str]:
    """Check if a log message matches a habit."""
    log_message = log_message.strip()
    habit_name = habit_name.strip()

    # Exact match
    if log_message == habit_name:
        return ""

    # Parametric match: habit_name:param
    if log_message.startswith(habit_name + ":"):
        param = log_message[len(habit_name) + 1 :].strip()
        # Extract only the first word after the colon
        if param:
            # Get the first word (split by space and take first part)
            first_word = param.split()[0] if param else ""
            return first_word if first_word else None

    return None


def loop_configure_parser(p: argparse.ArgumentParser) -> None:
    subparsers = p.add_subparsers(dest="loop_subcommand", help="loop subcommands")

    # add subcommand
    add_parser = subparsers.add_parser("add", help="Add a new habit")
    add_parser.add_argument(
        "--title",
        "-t",
        required=True,
        help="Habit name",
    )
    add_parser.add_argument(
        "--freq",
        "-f",
        required=True,
        help="Frequency: 'daily' for every day, or comma-separated days like 'mon,tue,sat'",
    )

    # today subcommand
    subparsers.add_parser("today", help="Show today's habit status")

    # statistics subcommand
    stats_parser = subparsers.add_parser(
        "statistics", help="Show completion statistics"
    )
    stats_parser.add_argument(
        "--since",
        help="Only include logs starting on/after this date (YYYY-MM-DD)",
    )
    stats_parser.add_argument(
        "--until",
        help="Only include logs up to/on this date (YYYY-MM-DD)",
    )


def loop_run(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "loop_subcommand", None)

    if subcommand == "add":
        name = args.title.strip()
        frequency = args.freq.strip()

        if not name:
            print("Error: habit name cannot be empty")
            return 1

        # Load existing habits
        habits = storage.load_habits_csv()

        # Check if habit already exists
        for h in habits:
            if h.get("name") == name:
                print(f"Error: Habit '{name}' already exists")
                return 1

        # Add new habit with creation timestamp
        habits.append(
            {
                "name": name,
                "frequency": frequency,
                "created_at": dt.datetime.now(),
            }
        )
        storage.save_habits_csv(habits)
        print(f"Added habit '{name}' with frequency '{frequency}'")
        return 0

    elif subcommand == "today":
        today = dt.date.today()

        # Load all habits
        habits = storage.load_habits_csv()

        if not habits:
            print(
                "No habits defined. Use 'hiper loop add --title <name> --freq <frequency>' to add one."
            )
            return 0

        # Filter habits to only those scheduled for today
        today_habits: List[Dict[str, object]] = []
        for habit in habits:
            frequency_obj = habit.get("frequency", "")
            frequency = str(frequency_obj) if frequency_obj is not None else ""
            if _is_habit_scheduled_today(frequency):
                today_habits.append(habit)

        if not today_habits:
            print(f"No habits scheduled for today ({today.strftime('%Y-%m-%d')})")
            return 0

        # Load today's logs
        logs = storage.load_log_csv()
        today_logs: list[str] = []
        for log in logs:
            ts = log.get("timestamp")
            if isinstance(ts, dt.datetime) and ts.date() == today:
                msg_obj = log.get("message", "")
                msg = str(msg_obj) if msg_obj is not None else ""
                today_logs.append(msg.strip())

        # Check each habit scheduled for today
        done_habits: List[Dict[str, object]] = []
        not_done_habits: List[Dict[str, object]] = []

        for habit in today_habits:
            habit_name_obj = habit.get("name", "")
            habit_name = str(habit_name_obj) if habit_name_obj is not None else ""
            # Check if any log message matches this habit (exact or parametric)
            is_done = False
            for log_msg in today_logs:
                if _check_habit_match(log_msg, habit_name) is not None:
                    is_done = True
                    break
            if is_done:
                done_habits.append(habit)
            else:
                not_done_habits.append(habit)

        # Display results
        print("=" * 50)
        print(f"Habits for {today.strftime('%Y-%m-%d')} ({_get_today_day_abbr()})")
        print("=" * 50)

        if done_habits:
            print("\n✓ Done:")
            for habit in done_habits:
                name_obj = habit.get("name", "")
                freq_obj = habit.get("frequency", "")
                name = str(name_obj) if name_obj is not None else ""
                freq = str(freq_obj) if freq_obj is not None else ""
                print(f"  {name} ({freq})")

        if not_done_habits:
            print("\n✗ Not done:")
            for habit in not_done_habits:
                name_obj = habit.get("name", "")
                freq_obj = habit.get("frequency", "")
                name = str(name_obj) if name_obj is not None else ""
                freq = str(freq_obj) if freq_obj is not None else ""
                print(f"  {name} ({freq})")

        return 0

    elif subcommand == "statistics":
        # Parse --since date
        since_date: Optional[dt.date] = None
        if args.since:
            try:
                since_date = dt.datetime.strptime(args.since.strip(), "%Y-%m-%d").date()
            except ValueError:
                print(
                    f"Error: invalid --since date '{args.since}'. Use YYYY-MM-DD format"
                )
                return 1

        # Parse --until date
        until_date: Optional[dt.date] = None
        if args.until:
            try:
                until_date = dt.datetime.strptime(args.until.strip(), "%Y-%m-%d").date()
            except ValueError:
                print(
                    f"Error: invalid --until date '{args.until}'. Use YYYY-MM-DD format"
                )
                return 1

        # Load all habits
        habits = storage.load_habits_csv()

        if not habits:
            print("No habits defined.")
            return 0

        # Load all logs
        logs = storage.load_log_csv()

        # Filter logs by date range if --since or --until is provided
        if since_date or until_date:
            filtered_logs: List[Dict[str, object]] = []
            for log in logs:
                ts = log.get("timestamp")
                if not isinstance(ts, dt.datetime):
                    continue
                log_date = ts.date()
                # Apply since filter
                if since_date and log_date < since_date:
                    continue
                # Apply until filter
                if until_date and log_date > until_date:
                    continue
                filtered_logs.append(log)
            logs = filtered_logs

        # Build a map of completed dates for each habit
        # For parametric habits, store the parameter value for each date
        habit_completed_dates: Dict[str, Dict[dt.date, Optional[str]]] = {}
        for log in logs:
            ts = log.get("timestamp")
            if not isinstance(ts, dt.datetime):
                continue
            msg_obj = log.get("message", "")
            msg = str(msg_obj) if msg_obj is not None else ""
            msg = msg.strip()
            if msg:
                # Check if this log message matches any habit
                for habit in habits:
                    habit_name_obj = habit.get("name", "")
                    habit_name = (
                        str(habit_name_obj) if habit_name_obj is not None else ""
                    )
                    param = _check_habit_match(msg, habit_name)
                    if param is not None:
                        if habit_name not in habit_completed_dates:
                            habit_completed_dates[habit_name] = {}
                        # Store the parameter value (empty string for non-parametric,
                        # actual value for parametric)
                        habit_completed_dates[habit_name][ts.date()] = (
                            param if param else None
                        )
                        break

        # Count occurrences of each habit (by unique dates completed)
        habit_counts: Dict[str, int] = {}
        for habit_name, completed_dates_dict in habit_completed_dates.items():
            habit_counts[habit_name] = len(completed_dates_dict)

        # Calculate completion rates
        print("=" * 50)
        print("Habit Completion Statistics")
        if since_date and until_date:
            print(
                f"From: {since_date.strftime('%Y-%m-%d')} to {until_date.strftime('%Y-%m-%d')}"
            )
        elif since_date:
            print(f"Since: {since_date.strftime('%Y-%m-%d')}")
        elif until_date:
            print(f"Until: {until_date.strftime('%Y-%m-%d')}")
        else:
            print("All time")
        print("=" * 50)

        # Print daily completion visualization for each habit
        for habit in habits:
            name_obj = habit.get("name", "")
            freq_obj = habit.get("frequency", "")
            created_at_obj = habit.get("created_at")
            name = str(name_obj) if name_obj is not None else ""
            freq = str(freq_obj) if freq_obj is not None else ""

            # Determine date range
            if since_date:
                start_date = since_date
            else:
                if isinstance(created_at_obj, dt.datetime):
                    start_date = created_at_obj.date()
                else:
                    start_date = dt.date.today() - dt.timedelta(days=30)

            if until_date:
                end_date = until_date
            else:
                end_date = dt.date.today()

            # Get scheduled days for this habit
            scheduled_days = _parse_frequency(freq)
            completed_dates_dict = habit_completed_dates.get(name, {})

            # Build visualization string
            visualization_parts: List[str] = []
            current_date = start_date
            while current_date <= end_date:
                day_abbr = _get_day_abbr_for_date(current_date)
                if day_abbr in scheduled_days:
                    # Habit is scheduled for this day
                    if current_date in completed_dates_dict:
                        param_value = completed_dates_dict[current_date]
                        if param_value:
                            # Parametric habit: display the parameter value
                            visualization_parts.append(f"[{param_value}]")
                        else:
                            # Non-parametric habit: display square
                            visualization_parts.append("[█]")
                    else:
                        visualization_parts.append("[ ]")
                else:
                    # Habit is not scheduled for this day
                    visualization_parts.append(".")
                current_date += dt.timedelta(days=1)

            # Print the visualization
            if visualization_parts:
                print(f"{name}: {''.join(visualization_parts)}")

        print("=" * 50)
        # Count expected occurrences based on frequency
        for habit in habits:
            name_obj = habit.get("name", "")
            freq_obj = habit.get("frequency", "")
            created_at_obj = habit.get("created_at")
            name = str(name_obj) if name_obj is not None else ""
            freq = str(freq_obj) if freq_obj is not None else ""

            # Calculate expected count based on frequency and date range
            scheduled_days = _parse_frequency(freq)
            completed_count: int = habit_counts.get(name, 0)

            # Calculate expected occurrences
            if since_date:
                start_date = since_date
            else:
                # Use creation date if available, otherwise use a default
                if isinstance(created_at_obj, dt.datetime):
                    start_date = created_at_obj.date()
                else:
                    # Fallback: assume habit was created 30 days ago
                    start_date = dt.date.today() - dt.timedelta(days=30)

            if until_date:
                end_date = until_date
            else:
                end_date = dt.date.today()

            expected = 0
            current_date = start_date
            while current_date <= end_date:
                day_abbr = _get_day_abbr_for_date(current_date)
                if day_abbr in scheduled_days:
                    expected += 1
                current_date += dt.timedelta(days=1)

            # Calculate completion rate
            if expected > 0:
                rate: float = (completed_count / expected) * 100
                print(f"{name}: {completed_count}/{expected} ({rate:.1f}%)")
            else:
                print(f"{name}: {completed_count}/0 (N/A)")

        return 0

    else:
        # No subcommand: show today's status and list all habits
        today_date = dt.date.today()

        # Load all habits
        all_habits = storage.load_habits_csv()

        if not all_habits:
            print(
                "No habits defined. Use 'hiper loop add --title <name> --freq <frequency>' to add one."
            )
            return 0

        # Show today's status first
        scheduled_today: List[Dict[str, object]] = []
        for habit in all_habits:
            frequency_obj = habit.get("frequency", "")
            frequency = str(frequency_obj) if frequency_obj is not None else ""
            if _is_habit_scheduled_today(frequency):
                scheduled_today.append(habit)

        if scheduled_today:
            # Load today's logs
            all_logs = storage.load_log_csv()
            today_messages: list[str] = []
            for log in all_logs:
                ts = log.get("timestamp")
                if isinstance(ts, dt.datetime) and ts.date() == today_date:
                    msg_obj = log.get("message", "")
                    msg = str(msg_obj) if msg_obj is not None else ""
                    today_messages.append(msg.strip())

            # Check each habit scheduled for today
            completed: List[Dict[str, object]] = []
            pending: List[Dict[str, object]] = []

            for habit in scheduled_today:
                habit_name_obj = habit.get("name", "")
                habit_name = str(habit_name_obj) if habit_name_obj is not None else ""
                # Check if any log message matches this habit (exact or parametric)
                is_completed = False
                for log_msg in today_messages:
                    if _check_habit_match(log_msg, habit_name) is not None:
                        is_completed = True
                        break
                if is_completed:
                    completed.append(habit)
                else:
                    pending.append(habit)

            # Display today's results
            print("=" * 50)
            print(
                f"Habits for {today_date.strftime('%Y-%m-%d')} ({_get_today_day_abbr()})"
            )
            print("=" * 50)

            if completed:
                print("\n✓ Done:")
                for habit in completed:
                    name_obj = habit.get("name", "")
                    freq_obj = habit.get("frequency", "")
                    name = str(name_obj) if name_obj is not None else ""
                    freq = str(freq_obj) if freq_obj is not None else ""
                    print(f"  {name} ({freq})")

            if pending:
                print("\n✗ Not done:")
                for habit in pending:
                    name_obj = habit.get("name", "")
                    freq_obj = habit.get("frequency", "")
                    name = str(name_obj) if name_obj is not None else ""
                    freq = str(freq_obj) if freq_obj is not None else ""
                    print(f"  {name} ({freq})")
        else:
            print("=" * 50)
            print(f"No habits scheduled for today ({today_date.strftime('%Y-%m-%d')})")
            print("=" * 50)

        # Show all habits with frequencies
        print("\n" + "=" * 50)
        print("All Habits")
        print("=" * 50)
        for habit in all_habits:
            name_obj = habit.get("name", "")
            freq_obj = habit.get("frequency", "")
            name = str(name_obj) if name_obj is not None else ""
            freq = str(freq_obj) if freq_obj is not None else ""
            print(f"  {name}: {freq}")

        return 0


def get_command() -> Command:
    return Command(
        name="loop",
        help="Manage habits and track daily completion.",
        description="Add habits and check today's completion status.",
        configure_parser=loop_configure_parser,
        run=loop_run,
    )
