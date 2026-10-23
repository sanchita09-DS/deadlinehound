"""Turn a JSON list of events into an .ics calendar file.

Usage: python make_ics.py events.json deadlines.ics
Each event needs: title, date (YYYY-MM-DD). Optional: time (HH:MM), action,
link, sender, evidence.
"""

import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone


def _s(value):
    """Return clean text; None and non-text values become an empty string."""
    return value.strip() if isinstance(value, str) else ""


def _escape(text):
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line):
    parts = [line[:70]] + [" " + line[index:index + 69] for index in range(70, len(line), 69)]
    return "\r\n".join(parts)


def build_ics(events):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DeadlineHound//EN",
        "CALSCALE:GREGORIAN",
    ]
    for event in events:
        day = date.fromisoformat(_s(event.get("date")))
        title, time_s = _s(event.get("title")), _s(event.get("time"))
        uid = hashlib.sha1(f"{title}{day}{time_s}".encode()).hexdigest()[:16]
        notes = [
            _s(event.get("action")),
            _s(event.get("link")),
            "From: " + _s(event.get("sender")) if _s(event.get("sender")) else "",
            'Said: "' + _s(event.get("evidence")) + '"' if _s(event.get("evidence")) else "",
        ]
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@deadlinehound",
            f"DTSTAMP:{stamp}",
            "SUMMARY:" + _escape(title),
            "DESCRIPTION:" + _escape("\n".join(note for note in notes if note)),
        ]
        if time_s:
            start = datetime.strptime(f"{day} {time_s}", "%Y-%m-%d %H:%M")
            lines += [
                f"DTSTART:{start:%Y%m%dT%H%M%S}",
                f"DTEND:{start + timedelta(hours=1):%Y%m%dT%H%M%S}",
            ]
        else:
            lines += [
                f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
                f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
            ]
        lines += [
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Due tomorrow",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def main():
    if len(sys.argv) != 3:
        print("Usage: python make_ics.py events.json deadlines.ics", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as handle:
        events = json.load(handle)
    with open(sys.argv[2], "w", encoding="utf-8", newline="") as handle:
        handle.write(build_ics(events))
    print(f"Wrote {len(events)} events to {sys.argv[2]}")


if __name__ == "__main__":
    main()
