import argparse
import datetime as dt
from typing import Dict, List, Optional

from .. import config, storage
from . import Command
from .set import DEFAULT_WORK_PER_DAY


def _get_seconds_per_work_day() -> int:
    """Read configured work-per-day duration (defaults to 8h)."""
    work_per_day = config.get_config("work_per_day", DEFAULT_WORK_PER_DAY)
    return storage.parse_duration(work_per_day)


def _calculate_start_by(
    estimate_seconds: int, deadline: dt.date, time_worked_seconds: int
) -> dt.date:
    """Calculate the latest start date considering estimate, deadline, and time already worked.

    Deadline day is not workable. We can work 8 hours per day.
    """
    remaining_seconds = estimate_seconds - time_worked_seconds
    seconds_per_day = _get_seconds_per_work_day()
    if remaining_seconds <= 0:
        # Already done, start immediately
        return dt.date.today()

    # Calculate days needed (ceiling division)
    days_needed = (remaining_seconds + seconds_per_day - 1) // seconds_per_day

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


def build_goal_summary(goal: Dict[str, object]) -> Optional[Dict[str, object]]:
    """Return a normalized goal summary for listing."""
    title_obj = goal.get("title")
    if not isinstance(title_obj, str) or not title_obj:
        return None

    estimate_seconds_obj = goal.get("estimate_seconds", 0)
    estimate_seconds = (
        estimate_seconds_obj if isinstance(estimate_seconds_obj, int) else 0
    )

    estimate_timestamp = goal.get("estimate_timestamp")
    if isinstance(estimate_timestamp, dt.datetime):
        time_worked_seconds = storage.get_time_worked_for_title(
            title_obj, after_timestamp=estimate_timestamp
        )
    else:
        time_worked_seconds = storage.get_time_worked_for_title(title_obj)

    deadline_obj = goal.get("deadline")
    start_by_obj = goal.get("start_by")
    if isinstance(deadline_obj, dt.date) and estimate_seconds > 0:
        start_by_obj = _calculate_start_by(
            estimate_seconds, deadline_obj, time_worked_seconds
        )
    else:
        start_by_obj = start_by_obj if isinstance(start_by_obj, dt.date) else None

    return {
        "title": title_obj,
        "estimate_seconds": estimate_seconds,
        "estimate": storage.format_hms(estimate_seconds)
        if estimate_seconds > 0
        else "",
        "time_worked_seconds": time_worked_seconds,
        "time_worked": storage.format_hms(time_worked_seconds),
        "remaining": storage.format_hms(max(0, estimate_seconds - time_worked_seconds))
        if estimate_seconds > 0
        else "",
        "deadline": deadline_obj if isinstance(deadline_obj, dt.date) else None,
        "start_by": start_by_obj if isinstance(start_by_obj, dt.date) else None,
    }


def _list_goals(goals: List[Dict[str, object]], show_all: bool) -> int:
    # Pair the original goal dict with its summary so we can sort and still
    # reuse the detailed printer.
    summaries: List[tuple[Dict[str, object], Dict[str, object]]] = []
    for goal in goals:
        built = build_goal_summary(goal)
        if not built:
            continue
        if not show_all:
            est = built.get("estimate_seconds")
            if not (isinstance(est, int) and est > 0):
                continue
        summaries.append((built, goal))

    if not summaries:
        print(
            "No goals found with current estimates."
            if not show_all
            else "No goals found in goals.csv."
        )
        return 0

    summaries = sorted(
        summaries,
        key=lambda pair: (
            pair[0]["start_by"] if pair[0].get("start_by") else dt.date.max,
            pair[0]["deadline"] if pair[0].get("deadline") else dt.date.max,
            pair[0]["title"],
        ),
    )

    header = "All goals:" if show_all else "Goals with current estimates:"
    print(header)
    if show_all:
        # Original compact one-line style for --all
        for summary, _goal in summaries:
            parts = [
                f"{summary['title']}",
                f"estimate {summary['estimate']}"
                if summary.get("estimate")
                else "estimate (not set)",
                f"worked {summary['time_worked']}",
                f"remaining {summary['remaining']}"
                if summary.get("remaining")
                else "remaining (n/a)",
            ]
            deadline_obj = summary.get("deadline")
            if isinstance(deadline_obj, dt.date):
                parts.append(f"deadline {deadline_obj.strftime('%Y-%m-%d')}")
            start_by_obj = summary.get("start_by")
            if isinstance(start_by_obj, dt.date):
                parts.append(f"start by {start_by_obj.strftime('%Y-%m-%d')}")
            print("  - " + ", ".join(parts))
    else:
        # Detailed block for goals with current estimates
        for idx, (summary, goal) in enumerate(summaries):
            title = summary["title"] if isinstance(summary["title"], str) else ""
            _print_goal_details(title, goal)
            if idx < len(summaries) - 1:
                print()

    return 0


def _print_goal_details(title: str, goal: Dict[str, object]) -> None:
    summary = build_goal_summary(goal)

    # Totals
    total_time_worked_seconds = storage.get_time_worked_for_title(title)
    total_time_worked = storage.format_hms(total_time_worked_seconds)

    estimate_timestamp = goal.get("estimate_timestamp")
    if isinstance(estimate_timestamp, dt.datetime):
        time_worked_seconds = storage.get_time_worked_for_title(
            title, after_timestamp=estimate_timestamp
        )
    else:
        time_worked_seconds_obj = summary.get("time_worked_seconds") if summary else 0
        time_worked_seconds = (
            time_worked_seconds_obj if isinstance(time_worked_seconds_obj, int) else 0
        )
    time_worked = storage.format_hms(time_worked_seconds)

    print(f"Goal: {title}")
    print(f"  Total time worked: {total_time_worked}")
    if isinstance(estimate_timestamp, dt.datetime):
        print(f"  Time worked (after estimate): {time_worked}")
    else:
        print(f"  Time worked: {time_worked}")

    if not summary:
        print("  Estimate: (not set)")
        print("  Deadline: (not set)")
        print("  Start by: (not set)")
        return

    estimate_obj = summary.get("estimate_seconds", 0)
    deadline_obj = summary.get("deadline")
    start_by_obj = summary.get("start_by")

    if isinstance(estimate_obj, int) and estimate_obj > 0:
        estimate = storage.format_hms(estimate_obj)
        remaining_seconds = max(0, int(estimate_obj) - int(time_worked_seconds))
        remaining = storage.format_hms(remaining_seconds)

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


def prefokus_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title",
        "-t",
        required=False,
        help="Goal title",
    )
    p.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="List all goals even without an estimate",
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
    title = (args.title or "").strip()
    # When no title is provided, list goals.
    if not title:
        if args.estimate or args.deadline:
            print("Error: --title is required when setting an estimate or deadline")
            return 1

        goals = _update_time_worked(storage.load_goals_csv())
        return _list_goals(goals, show_all=args.all)

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

    # Display result using summary helper
    _print_goal_details(title, goal)
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
