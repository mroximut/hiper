import datetime as dt
from typing import Optional


def time_of_day_message(now: dt.datetime) -> str:
    hour = now.hour
    if 5 <= hour < 12:
        return "Good morning — set your intention and start small."
    if 12 <= hour < 17:
        return "Good afternoon — keep momentum, one focused block at a time."
    if 17 <= hour < 22:
        return "Good evening — wrap up with clarity, avoid new rabbit holes."
    return "Late hours — protect energy; short, deliberate focus wins."


def elapsed_message(seconds: int) -> str | None:
    milestones = {
        60: "1 min — settling in.",
        5 * 60: "5 min — friction fades.",
        10 * 60: "10 min — you're in.",
        15 * 60: "15 min — keep the streak.",
        20 * 60: "20 min — clarity compounds.",
        25 * 60: "25 min — classic pomodoro, consider a short break soon.",
        30 * 60: "30 min — deep work zone.",
        45 * 60: "45 min — powerful block, plan your next step.",
        60 * 60: "60 min — strong hour, write a quick summary.",
    }
    return milestones.get(seconds)


def instructions_line() -> str:
    return "Press Space to pause."


def started_at_line(start_time: dt.datetime) -> str:
    return f"Started at {start_time.strftime('%H:%M:%S')}"


def saved_session_line(formatted_duration: str) -> str:
    return f"Saved session: {formatted_duration}"


def cancelled_line() -> str:
    return "Session cancelled; nothing saved."


def exited_without_saving_line() -> str:
    return "Exited without saving."


def interrupted_line() -> str:
    return "Interrupted. Use --auto-save to save on Ctrl+C."


def paused_line() -> str:
    return "Paused. (save | discard | resume | quit)"


def command_prompt() -> str:
    return "> "


def saved_path_line(path: str) -> str:
    return f"Saved to: {path}"


def stats_header(name_filter: Optional[str] = None) -> str:
    if name_filter:
        return f"Statistics for {name_filter}"
    return "Statistics"


def stats_line(key: str, value: str) -> str:
    return f"{key}: {value}"


def resuming_line(pause_duration_formatted: str, resume_time: dt.datetime) -> str:
    return f"Paused for {pause_duration_formatted} — resuming at {resume_time.strftime('%H:%M:%S')}\n"
