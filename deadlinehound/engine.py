"""Local chat parsing, Ollama extraction, verification, and iCalendar output."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3.2:1b"

_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s+-\s+"
    r"([^:]+):\s?(.*)$"
)
_IPHONE = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?\s*[APap][Mm])\]\s+([^:]+):\s?(.*)$"
)
_ACTION = re.compile(
    r"\b(submit|register|apply|upload|pay|bring|attend|join|complete|finish|"
    r"deadline|due|last date|close[sd]?|meeting|exam|interview|report)\b",
    re.IGNORECASE,
)
_TIME_HINT = re.compile(
    r"\b(today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|next week|next month|by\s+\d{1,2}|\d{1,2}/\d{1,2}|"
    r"\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))\b",
    re.IGNORECASE,
)
_CLOCK_TIME = re.compile(
    r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b|\b(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:am|pm)\b",
    re.IGNORECASE,
)


def _parse_sent(day_text: str, time_text: str) -> datetime | None:
    day_formats = ("%d/%m/%y", "%d/%m/%Y")
    time_formats = ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p")
    day_value = None
    for fmt in day_formats:
        try:
            day_value = datetime.strptime(day_text, fmt).date()
            break
        except ValueError:
            continue
    if day_value is None:
        return None
    normalized_time = re.sub(r"\s+", " ", time_text.strip().upper())
    time_value = None
    for fmt in time_formats:
        try:
            time_value = datetime.strptime(normalized_time, fmt).time()
            break
        except ValueError:
            continue
    if time_value is None:
        return None
    return datetime.combine(day_value, time_value)


def parse_chat(text: str) -> list[dict]:
    """Parse common Android and iPhone day/month WhatsApp text exports."""
    messages: list[dict] = []
    for line in text.splitlines():
        match = _ANDROID.match(line) or _IPHONE.match(line)
        if match:
            sent = _parse_sent(match.group(1), match.group(2))
            sender, body = match.group(3).strip(), match.group(4).strip()
            if sent and body:
                messages.append({"sent": sent, "sender": sender, "text": body})
        elif messages and line.strip():
            messages[-1]["text"] += " " + line.strip()
    return messages


def find_candidates(messages: list[dict]) -> list[dict]:
    """Keep messages containing both an action clue and a date/time clue."""
    return [
        message
        for message in messages
        if _ACTION.search(message["text"]) and _TIME_HINT.search(message["text"])
    ][:25]


def _json_array(raw: str) -> list:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start = cleaned.find("[")
    if start < 0:
        raise ValueError("The model did not return a JSON list.")
    value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    if not isinstance(value, list):
        raise ValueError("The model response was not a JSON list.")
    return value


def _same_words(first: str, second: str) -> bool:
    normalize = lambda value: " ".join(value.split()).casefold()
    return normalize(first) in normalize(second)


def _verified_events(proposed: list, candidates: list[dict]) -> list[dict]:
    accepted = []
    seen = set()
    today = date.today()
    for item in proposed:
        if not isinstance(item, dict):
            continue
        try:
            candidate_id = int(item.get("candidate_id"))
            candidate = candidates[candidate_id]
            event_day = date.fromisoformat(str(item.get("date", "")))
        except (ValueError, TypeError, IndexError):
            continue
        title = str(item.get("title", "")).strip()[:120]
        evidence = str(item.get("evidence", "")).strip()
        action = str(item.get("action", "")).strip()[:240]
        if action.casefold() in {"none", "null", "n/a", "unknown"}:
            action = ""
        time_value = str(item.get("time", "")).strip()
        if not title or not evidence or not _same_words(evidence, candidate["text"]):
            continue
        if event_day < today or event_day < candidate["sent"].date():
            continue
        if time_value and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time_value):
            time_value = ""
        # Do not let the model turn a date-only deadline into a timed midnight event.
        if not _CLOCK_TIME.search(candidate["text"]):
            time_value = ""
        duplicate_key = (
            candidate_id,
            event_day.isoformat(),
            " ".join(evidence.casefold().split()),
            time_value,
        )
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)
        accepted.append(
            {
                "title": title,
                "date": event_day.isoformat(),
                "time": time_value,
                "action": action,
                "evidence": evidence,
                "sender": candidate["sender"],
            }
        )
    return accepted


def extract_events(messages: list[dict]) -> tuple[list[dict], int]:
    candidates = find_candidates(messages)
    if not candidates:
        return [], 0
    numbered = [
        {
            "candidate_id": index,
            "sent": message["sent"].isoformat(sep=" "),
            "sender": message["sender"],
            "text": message["text"],
        }
        for index, message in enumerate(candidates)
    ]
    prompt = (
        "Find real future deadlines, meetings, or dated tasks in these chat messages. "
        "Return only a JSON array. Each item must have candidate_id (integer), title, "
        "date (YYYY-MM-DD), time (24-hour HH:MM or empty), action, and evidence. "
        "Evidence must be an exact quote copied from that candidate's text. "
        "Resolve relative dates from the candidate's sent timestamp. Do not guess; "
        "omit unclear events. If none, return []. Messages: "
        + json.dumps(numbered, ensure_ascii=False)
    )
    request_data = json.dumps(
        {"model": MODEL, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL, data=request_data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            answer = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach Ollama. Open the Ollama app and make sure it is running."
        ) from exc
    raw = answer.get("response", "")
    return _verified_events(_json_array(raw), candidates), len(candidates)


def make_ics(events: list[dict]) -> bytes:
    """Create an iCalendar file with one-day reminders."""
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DeadlineHound//EN", "CALSCALE:GREGORIAN"]
    for index, event in enumerate(events):
        event_day = date.fromisoformat(event["date"])
        lines.extend(["BEGIN:VEVENT", f"UID:deadlinehound-{index}-{event_day.isoformat()}@local"])
        if event.get("time"):
            start = datetime.strptime(event["date"] + " " + event["time"], "%Y-%m-%d %H:%M")
            lines.append("DTSTART:" + start.strftime("%Y%m%dT%H%M%S"))
        else:
            lines.append("DTSTART;VALUE=DATE:" + event_day.strftime("%Y%m%d"))
        lines.extend(
            [
                "SUMMARY:" + escape(event["title"]),
                "DESCRIPTION:" + escape(event.get("action", "")),
                "BEGIN:VALARM",
                "TRIGGER:-P1D",
                "ACTION:DISPLAY",
                "DESCRIPTION:Deadline reminder",
                "END:VALARM",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
