import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "skills" / "chat-deadline-extractor" / "scripts"))

from deadlinehound.extractor import verify  # noqa: E402
from make_ics import build_ics  # noqa: E402
from parse_chat import find_candidates, parse_chat  # noqa: E402

CHAT = (ROOT / "sample_data" / "sample_chat.txt").read_text(encoding="utf-8")


def test_multiline_message_is_joined():
    messages = parse_chat(CHAT)
    assert len(messages) == 7
    assert "Make sure your repo is public." in messages[3]["text"]


def test_day_first_dates():
    assert parse_chat(CHAT)[0]["time"] == datetime(2026, 10, 23, 9, 12)


def test_candidate_filter_skips_small_talk():
    candidate_texts = [candidate["text"] for candidate in find_candidates(parse_chat(CHAT))]
    assert len(candidate_texts) == 4
    assert not any("thanks sir" in text for text in candidate_texts)


def test_verify_rejects_invented_evidence():
    candidate = {"text": "Submit before 31/10/26.", "sender": "A"}
    sent = datetime(2026, 10, 23, 9, 0)
    invented = [
        {"title": "X", "date": "2026-10-31", "evidence": "pay 500 rupees"}
    ]
    assert verify(invented, candidate, sent) == []


def test_verify_accepts_real_evidence_and_drops_past_dates():
    sent = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    deadline = sent.date() + timedelta(days=8)
    deadline_text = deadline.strftime("%d/%m/%Y")
    candidate = {"text": f"Submit before {deadline_text}.", "sender": "A"}
    valid = [
        {
            "title": "Submit",
            "date": deadline.isoformat(),
            "time": "23:59",
            "evidence": f"Submit before {deadline_text}",
        }
    ]
    past_day = sent.date() - timedelta(days=1)
    past_text = past_day.strftime("%d/%m/%Y")
    past_candidate = {"text": f"Submit before {past_text}.", "sender": "A"}
    past = [
        {
            "title": "Old",
            "date": past_day.isoformat(),
            "evidence": f"Submit before {past_text}",
        }
    ]
    assert len(verify(valid, candidate, sent)) == 1
    assert verify(past, past_candidate, sent) == []


def test_ics_has_events_and_reminders():
    events = [
        {"title": "Submit repo", "date": "2026-10-31", "time": "23:59"},
        {"title": "Meeting", "date": "2026-10-26", "time": float("nan")},
    ]
    ics = build_ics(events)
    assert ics.count("BEGIN:VEVENT") == 2
    assert "DTSTART:20261031T235900" in ics
    assert "DTSTART;VALUE=DATE:20261026" in ics
    assert "TRIGGER:-P1D" in ics
