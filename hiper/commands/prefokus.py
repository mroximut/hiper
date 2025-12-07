import argparse
import datetime as dt
from typing import Dict, List, Optional

from .. import storage
from . import Command

HOURS_PER_DAY = 8
SECONDS_PER_DAY = HOURS_PER_DAY * 3600


def _calculate_start_by(
    estimate_seconds: int, deadline: dt.date, time_worked_seconds: int
) -> dt.date:
    """Calculate the latest start date considering estimate, deadline, and time already worked.

    Deadline day is not workable. We can work 8 hours per day.
    """
    remaining_seconds = estimate_seconds - time_worked_seconds
    if remaining_seconds <= 0:
        # Already done, start immediately
        return dt.date.today()

    # Calculate days needed (ceiling division)
    days_needed = (remaining_seconds + SECONDS_PER_DAY - 1) // SECONDS_PER_DAY

    # Deadline day is not workable, so we count backwards from the day before deadline
    # If deadline is 2025-12-09, we can work on 2025-12-08, 2025-12-07, etc.
    last_workable_day = deadline - dt.timedelta(days=1)

    # Calculate start_by: go back (days_needed - 1) days from last_workable_day
    # If we need 3 days and last workable is 2025-12-08:
    # Day 1: 2025-12-08
    # Day 2: 2025-12-07
    # Day 3: 2025-12-06
    # So start_by = 2025-12-06
    start_by = last_workable_day - dt.timedelta(days=days_needed - 1)

    return start_by


def _update_time_worked(goals: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Update time_worked_seconds for all goals based on current sessions.csv."""
    for goal in goals:
        title_obj = goal.get("title")
        if not isinstance(title_obj, str):
            continue
        goal["time_worked_seconds"] = storage.get_time_worked_for_title(title_obj)
        # Recalculate start_by with updated time_worked
        estimate_obj = goal.get("estimate_seconds")
        deadline_obj = goal.get("deadline")
        time_worked_obj = goal.get("time_worked_seconds", 0)

        if (
            isinstance(estimate_obj, int)
            and estimate_obj > 0
            and isinstance(deadline_obj, dt.date)
            and isinstance(time_worked_obj, int)
        ):
            goal["start_by"] = _calculate_start_by(
                estimate_obj,
                deadline_obj,
                time_worked_obj,
            )
    return goals


def prefokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title",
        "-t",
        required=True,
        help="Goal title",
    )
    p.add_argument(
        "--estimate",
        "-e",
        help="Estimated time needed (e.g., 20h, 1h30m). Required for new goals.",
    )
    p.add_argument(
        "--deadline",
        "-d",
        help="Deadline date (YYYY-MM-DD). Optional. Deadline day is not workable.",
    )


def prefokus_run(args: argparse.Namespace) -> int:
    title = args.title.strip()
    if not title:
        print("Error: title cannot be empty")
        return 1

    # Load existing goals
    goals = storage.load_goals_csv()

    # Find existing goal or create new one
    goal: Optional[Dict[str, object]] = None
    for g in goals:
        if g["title"] == title:
            goal = g
            break

    if goal is None:
        # Create new goal
        if not args.estimate:
            print("Error: --estimate is required for new goals")
            return 1

        try:
            estimate_seconds = storage.parse_duration(args.estimate)
        except ValueError as e:
            print(f"Error: invalid estimate '{args.estimate}': {e}")
            return 1

        deadline: Optional[dt.date] = None
        if args.deadline:
            try:
                deadline = dt.datetime.strptime(args.deadline, "%Y-%m-%d").date()
            except ValueError:
                print(
                    f"Error: invalid deadline format '{args.deadline}'. Use YYYY-MM-DD"
                )
                return 1

        # Set timestamp when estimate is first created
        estimate_timestamp = dt.datetime.now()
        # Get time worked after timestamp (should be 0 for new goals)
        time_worked_seconds = storage.get_time_worked_for_title(
            title, after_timestamp=estimate_timestamp
        )
        start_by: Optional[dt.date] = None
        if deadline:
            start_by = _calculate_start_by(
                estimate_seconds, deadline, time_worked_seconds
            )

        goal = {
            "title": title,
            "estimate_seconds": estimate_seconds,
            "estimate_formatted": storage.format_hms(estimate_seconds),
            "estimate_timestamp": estimate_timestamp,
            "deadline": deadline,
            "time_worked_seconds": time_worked_seconds,
            "time_worked_formatted": storage.format_hms(time_worked_seconds),
            "start_by": start_by,
        }
        goals.append(goal)
    else:
        # Update existing goal
        if args.estimate:
            try:
                goal["estimate_seconds"] = storage.parse_duration(args.estimate)
                goal["estimate_formatted"] = storage.format_hms(
                    goal["estimate_seconds"]
                )
                # Set new timestamp when estimate is updated
                goal["estimate_timestamp"] = dt.datetime.now()
            except ValueError as e:
                print(f"Error: invalid estimate '{args.estimate}': {e}")
                return 1

        if args.deadline:
            try:
                goal["deadline"] = dt.datetime.strptime(
                    args.deadline, "%Y-%m-%d"
                ).date()
            except ValueError:
                print(
                    f"Error: invalid deadline format '{args.deadline}'. Use YYYY-MM-DD"
                )
                return 1

        # Always update time_worked from sessions.csv (after estimate timestamp)
        estimate_timestamp = goal.get("estimate_timestamp")
        if isinstance(estimate_timestamp, dt.datetime):
            goal["time_worked_seconds"] = storage.get_time_worked_for_title(
                title, after_timestamp=estimate_timestamp
            )
        else:
            # If no timestamp, use all time worked (backward compatibility)
            goal["time_worked_seconds"] = storage.get_time_worked_for_title(title)
        goal["time_worked_formatted"] = storage.format_hms(goal["time_worked_seconds"])

        # Recalculate start_by
        estimate_obj = goal.get("estimate_seconds")
        deadline_obj = goal.get("deadline")
        time_worked_obj = goal.get("time_worked_seconds", 0)

        if (
            isinstance(estimate_obj, int)
            and estimate_obj > 0
            and isinstance(deadline_obj, dt.date)
            and isinstance(time_worked_obj, int)
        ):
            goal["start_by"] = _calculate_start_by(
                estimate_obj,
                deadline_obj,
                time_worked_obj,
            )

    # Update time_worked for all goals (in case sessions changed)
    goals = _update_time_worked(goals)

    # Save goals
    storage.save_goals_csv(goals)

    # Display result
    estimate_obj = goal.get("estimate_seconds", 0)
    estimate_timestamp = goal.get("estimate_timestamp")

    # Get total time worked (all time for this title)
    total_time_worked_seconds = storage.get_time_worked_for_title(title)
    total_time_worked = storage.format_hms(total_time_worked_seconds)

    # Recalculate time_worked after timestamp for accurate remaining calculation
    if isinstance(estimate_timestamp, dt.datetime):
        time_worked_seconds = storage.get_time_worked_for_title(
            title, after_timestamp=estimate_timestamp
        )
    else:
        # If no timestamp, use all time worked (backward compatibility)
        time_worked_obj = goal.get("time_worked_seconds", 0)
        time_worked_seconds = (
            int(time_worked_obj) if isinstance(time_worked_obj, (int, str)) else 0
        )

    time_worked = storage.format_hms(time_worked_seconds)
    print(f"Goal: {title}")
    print(f"  Total time worked: {total_time_worked}")
    if isinstance(estimate_timestamp, dt.datetime):
        print(f"  Time worked (after estimate): {time_worked}")
    else:
        print(f"  Time worked: {time_worked}")

    deadline_obj = goal.get("deadline")
    start_by_obj = goal.get("start_by")

    if isinstance(estimate_obj, int) and estimate_obj > 0:
        estimate = storage.format_hms(estimate_obj)
        # Remaining = estimate - (time worked after timestamp)
        remaining_seconds = estimate_obj - time_worked_seconds
        remaining = storage.format_hms(max(0, remaining_seconds))

        print(f"  Estimate: {estimate}")
        if remaining_seconds > 0:
            print(f"  Remaining: {remaining}")
        else:
            print("  Remaining: 0 (completed!)")

        if isinstance(deadline_obj, dt.date):
            print(f"  Deadline: {deadline_obj.strftime('%Y-%m-%d')}")
            if isinstance(start_by_obj, dt.date):
                start_by_str = start_by_obj.strftime("%Y-%m-%d")
                print(f"  Start by: {start_by_str} morning")
            else:
                print("  Start by: (not calculated)")
        else:
            print("  Deadline: (not set)")
            print("  Start by: (not set - deadline required)")
    else:
        print("  Estimate: (not set)")
        print("  Deadline: (not set)")
        print("  Start by: (not set)")

    return 0


def get_command() -> Command:
    return Command(
        name="prefokus",
        help="Plan focus goals with estimates and optional deadlines",
        description="Create or update goals with time estimates and optional deadlines. "
        "If a deadline is provided, calculates when you should start working to meet it "
        "(assuming 8 hours of work per day).",
        configure_parser=prefokus_configure_parser,
        run=prefokus_run,
    )
