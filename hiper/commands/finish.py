import argparse

from .. import storage
from . import Command


def finish_configure_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title",
        "-t",
        required=True,
        help="Title of the goal to finish",
    )


def finish_run(args: argparse.Namespace) -> int:
    title = args.title.strip()
    if not title:
        print("Error: title cannot be empty")
        return 1

    # Load all goals
    goals = storage.load_goals_csv()

    # Find the goal with matching title
    goal_found = False
    for goal in goals:
        goal_title_obj = goal.get("title", "")
        if isinstance(goal_title_obj, str):
            goal_title = goal_title_obj.strip()
        else:
            goal_title = ""
        if goal_title == title:
            goal_found = True
            # Preserve only title, time_worked_seconds, and time_worked_formatted
            time_worked_seconds = goal.get("time_worked_seconds", 0)
            time_worked_formatted = goal.get("time_worked_formatted", "")

            # Clear all other fields
            goal["estimate_seconds"] = 0
            goal["estimate_formatted"] = ""
            goal["estimate_timestamp"] = None
            goal["deadline"] = None
            goal["start_by"] = None

            # Keep time_worked fields
            goal["time_worked_seconds"] = time_worked_seconds
            goal["time_worked_formatted"] = time_worked_formatted
            break

    if not goal_found:
        print(f"Error: goal with title '{title}' not found")
        return 1

    # Save the updated goals
    storage.save_goals_csv(goals)
    print(f"Finished goal '{title}': cleared all fields except time worked")
    return 0


def get_command() -> Command:
    return Command(
        name="finish",
        help="Finish a goal that has been estimated before.",
        description="Remove everything from a goal in goals.csv except for "
        "time_worked_seconds and time_worked_formatted",
        configure_parser=finish_configure_parser,
        run=finish_run,
    )
