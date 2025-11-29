import datetime as dt
import json
import os
from typing import Optional

from . import config


def _load_lang_from_config() -> str:
    return config.get_config("lang", "en")


# Simple i18n layer. Set via set_language()
_LANG: str = _load_lang_from_config()


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang or "en"


def save_language(lang: str) -> None:
    """Persist language setting to config file"""
    lang = lang or "en"
    config.set_config("lang", lang)
    set_language(lang)


def time_of_day_message(now: dt.datetime) -> str:
    return ""
    hour = now.hour
    texts = {
        "en": {
            "morning": "Good morning — set your intention and start small.",
            "afternoon": "Good afternoon — keep momentum, one focused block at a time.",
            "evening": "Good evening — wrap up with clarity, avoid new rabbit holes.",
            "late": "Late hours — protect energy; short, deliberate focus wins.",
        },
        # "tr": { ... }
    }
    t = texts.get(_LANG, texts["en"])
    if 5 <= hour < 12:
        return t["morning"]
    if 12 <= hour < 17:
        return t["afternoon"]
    if 17 <= hour < 22:
        return t["evening"]
    return t["late"]


def elapsed_message(seconds: int) -> str | None:
    return ""
    en_milestones = {
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
    milestones_by_lang = {
        "en": en_milestones,
        # "tr": { ... }
    }
    milestones = milestones_by_lang.get(_LANG, en_milestones)
    return milestones.get(seconds)


def instructions_line() -> str:
    texts = {
        "en": "Press Space to pause.",
    }
    return texts.get(_LANG, texts["en"])


def started_at_line(start_time: dt.datetime) -> str:
    return f"Started at {start_time.strftime('%H:%M:%S')}"


def saved_session_line(formatted_duration: str) -> str:
    templates = {
        "en": "Saved session: {duration}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(duration=formatted_duration)


def cancelled_line() -> str:
    texts = {
        "en": "Session cancelled; nothing saved.",
    }
    return texts.get(_LANG, texts["en"])


def exited_without_saving_line() -> str:
    texts = {
        "en": "Exited without saving.",
    }
    return texts.get(_LANG, texts["en"])


def interrupted_line() -> str:
    texts = {
        "en": "Interrupted. Use --auto-save to save on Ctrl+C.",
    }
    return texts.get(_LANG, texts["en"])


def paused_line(current_time: dt.datetime) -> str:
    templates = {
        "en": "Paused at {time}.",  # (save | discard | resume | quit)",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(time=current_time.strftime("%H:%M:%S"))


def command_prompt() -> str:
    prompts = {
        "en": "> ",
    }
    return prompts.get(_LANG, prompts["en"])


def saved_path_line(path: str) -> str:
    templates = {
        "en": "Saved to: {path}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(path=path)


def stats_header(title_filter: Optional[str] = None) -> str:
    if title_filter:
        templates = {"en": "Statistics {title}"}
        tmpl = templates.get(_LANG, templates["en"])
        return tmpl.format(title=title_filter)
    texts = {"en": "Statistics"}
    return texts.get(_LANG, texts["en"])


def stats_line(key: str, value: str) -> str:
    # Keep key/value formatting simple and language-agnostic
    return f"{key}: {value}"


def resuming_line(pause_duration_formatted: str, resume_time: dt.datetime) -> str:
    templates = {
        "en": "Paused for {pause}, resuming at {time}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(
        pause=pause_duration_formatted, time=resume_time.strftime("%H:%M:%S")
    )


# Errors and notices
def invalid_duration(message: str) -> str:
    templates = {
        "en": "Invalid duration: {msg}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(msg=message)


def invalid_start(message: str) -> str:
    templates = {
        "en": "Invalid start: {msg}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(msg=message)


def invalid_end(message: str) -> str:
    templates = {
        "en": "Invalid end: {msg}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(msg=message)


def language_set(lang: str) -> str:
    templates = {
        "en": "Language set to: {lang}",
    }
    tmpl = templates.get(_LANG, templates["en"])
    return tmpl.format(lang=lang)


# To add translations:
# - Create entries for your language code (e.g., "tr") alongside "en" in the
#   dictionaries above (templates/texts/prompts).
