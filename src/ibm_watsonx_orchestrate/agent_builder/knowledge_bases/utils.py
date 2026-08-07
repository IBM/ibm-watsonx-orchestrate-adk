"""Utility functions for knowledge base operations."""

from datetime import datetime, timezone

# NOTE: Knowledge scheduling deferred, but keeping commented for future use 
# def format_cron_pattern_human(pattern: str) -> str:
#     """
#     Format a cron pattern as a concise human-readable string.

#     Examples:
#         "*/60 * * * *"  -> "Every 60m"
#         "0 0 * * *"     -> "Every day at midnight"
#         "0 14 * * *"    -> "Every day at 2pm"
#         "0 9 * * 1"     -> "Every Monday at 9am"
#         "0 0 * * 1,3,5" -> "Every Mon, Wed, Fri at midnight"
#         "30 8 * * 1-5"  -> "Every weekday at 8:30am"

#     Falls back to the raw pattern if it cannot be parsed.
#     """
#     try:
#         if not croniter.is_valid(pattern):
#             return pattern

#         parts = pattern.strip().split()
#         if len(parts) != 5:
#             return pattern

#         minute_s, hour_s, dom_s, month_s, dow_s = parts

#         # --- Step / interval shorthand (e.g. */60, */30) ---
#         if (minute_s.startswith("*/") and hour_s == "*" and
#                 dom_s == "*" and month_s == "*" and dow_s == "*"):
#             interval = int(minute_s[2:])
#             return f"Every {interval}m"

#         if (hour_s.startswith("*/") and minute_s == "0" and
#                 dom_s == "*" and month_s == "*" and dow_s == "*"):
#             interval = int(hour_s[2:])
#             return f"Every {interval}h"

#         # --- Helpers ---
#         _DAY_NAMES = {
#             "0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed",
#             "4": "Thu", "5": "Fri", "6": "Sat",
#             "7": "Sun",
#         }

#         def _time_str(h: int, m: int) -> str:
#             if m == 0:
#                 if h == 0:
#                     return "midnight"
#                 if h == 12:
#                     return "noon"
#                 suffix = "am" if h < 12 else "pm"
#                 return f"{h if h <= 12 else h - 12}{suffix}"
#             suffix = "am" if h < 12 else "pm"
#             display_h = h if h <= 12 else h - 12
#             if display_h == 0:
#                 display_h = 12
#             return f"{display_h}:{m:02d}{suffix}"

#         def _expand_dow(dow: str) -> list[str]:
#             """Expand a DOW field (e.g. '1-5', '1,3,5') to a list of short day names."""
#             names = []
#             for token in dow.split(","):
#                 if "-" in token:
#                     start, end = token.split("-")
#                     for d in range(int(start), int(end) + 1):
#                         names.append(_DAY_NAMES[str(d)])
#                 else:
#                     names.append(_DAY_NAMES[token])
#             return names

#         # --- Fixed time patterns ---
#         try:
#             h = int(hour_s)
#             m = int(minute_s)
#             time_label = _time_str(h, m)

#             # Every day
#             if dom_s == "*" and month_s == "*" and dow_s == "*":
#                 return f"Every day at {time_label}"

#             # Specific days of week
#             if dom_s == "*" and month_s == "*" and dow_s != "*":
#                 if dow_s == "1-5":
#                     return f"Every weekday at {time_label}"
#                 if dow_s == "0,6" or dow_s == "6,0":
#                     return f"Every weekend at {time_label}"
#                 days = ", ".join(_expand_dow(dow_s))
#                 return f"Every {days} at {time_label}"
#         except ValueError:
#             pass

#         # Fallback to raw pattern
#         return pattern
#     except Exception:
#         return pattern


def format_next_occurrence_relative(next_occurrence: str) -> str:
    """
    Format an ISO-8601 UTC timestamp as a human-readable relative string.

    Examples:
        "2026-07-02T14:00:00Z"  ->  "In 20m"
        "2026-07-03T09:00:00Z"  ->  "In 2h"
        "2026-07-09T00:00:00Z"  ->  "In 7d"

    Falls back to the raw string if it cannot be parsed.
    """
    try:
        # Parse ISO-8601 (with or without trailing Z)
        ts = next_occurrence.rstrip("Z")
        dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta_secs = int((dt - now).total_seconds())
        if delta_secs <= 0:
            return "Imminent"
        minutes = delta_secs // 60
        if minutes < 60:
            return f"In {minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"In {hours}h"
        days = hours // 24
        return f"In {days}d"
    except Exception:
        return next_occurrence