"""Read an exported WhatsApp chat and list messages that look like announcements.

Usage: python parse_chat.py chat.txt [--mdy]
Prints a JSON list of candidate messages. Dates are day/month unless --mdy.
"""

import json
import re
import sys
from datetime import datetime

LINE = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\]?"
    r"\s*[-\u2013]?\s*([^:]+?):\s(.*)$"
)
DATE_FORMATS = {
    True: ["%d/%m/%y", "%d/%m/%Y"],
    False: ["%m/%d/%y", "%m/%d/%Y"],
}
TIME_FORMATS = ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"]
ACTION = re.compile(
    r"deadline|last date|due|submit|submission|register|registration|apply|"
    r"before|till|until|reminder|mandatory|urgent|clos|expire|meeting|exam|form",
    re.I,
)
TIME_HINT = re.compile(
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mon|tue|wed|thu|fri|sat|sun|"
    r"tomorrow|today|tonight|\d{1,2}(st|nd|rd|th)\b|\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}\s?(am|pm)",
    re.I,
)


def parse_timestamp(date_s, time_s, dayfirst=True):
    time_s = " ".join(time_s.replace("\u202f", " ").split()).upper()
    for date_format in DATE_FORMATS[dayfirst]:
        for time_format in TIME_FORMATS:
            try:
                return datetime.strptime(f"{date_s} {time_s}", f"{date_format} {time_format}")
            except ValueError:
                continue
    return None


def parse_chat(text, dayfirst=True):
    """Turn raw export text into a list of {time, sender, text} messages."""
    messages = []
    for raw in text.splitlines():
        line = raw.replace("\u200e", "").lstrip("\ufeff")
        match = LINE.match(line)
        stamp = parse_timestamp(match.group(1), match.group(2), dayfirst) if match else None
        if match and stamp:
            messages.append(
                {"time": stamp, "sender": match.group(3).strip(), "text": match.group(4)}
            )
        elif messages:
            messages[-1]["text"] += "\n" + line
    return messages


def find_candidates(messages, min_len=25):
    """Keep messages with an action word AND a time hint (cheap filter, no AI)."""
    out = []
    for index, message in enumerate(messages):
        text = message["text"]
        if len(text) >= min_len and ACTION.search(text) and TIME_HINT.search(text):
            out.append(
                {
                    "id": index,
                    "sent": message["time"].strftime("%Y-%m-%dT%H:%M"),
                    "sender": message["sender"],
                    "text": text,
                }
            )
    return out


def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) != 1:
        print("Usage: python parse_chat.py chat.txt [--mdy]", file=sys.stderr)
        sys.exit(1)
    with open(args[0], encoding="utf-8", errors="ignore") as handle:
        messages = parse_chat(handle.read(), dayfirst="--mdy" not in sys.argv)
    print(json.dumps(find_candidates(messages), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
