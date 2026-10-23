# Export formats understood by `parse_chat.py`

The parser recognizes Android and iPhone WhatsApp text exports. Dates are day/month by default; pass `--mdy` for month/day dates.

| Platform | Example line |
| --- | --- |
| Android, 24-hour clock | `23/10/26, 11:10 - Name: message` |
| Android, 12-hour clock | `23/10/2026, 11:10 AM - Name: message` |
| iPhone, 12-hour clock | `[23/10/26, 11:10:05 AM] Name: message` |

Lines that do not begin with a recognized timestamp are appended to the previous message. The export does not contain a timezone, so treat parsed times as local chat/calendar times and ask the user if the timezone matters.

# Event JSON used by `make_ics.py`

```json
[
  {
    "title": "Submit repo",
    "date": "2026-10-31",
    "time": "23:59",
    "action": "Submit link",
    "link": "https://example.com/",
    "sender": "Organiser",
    "evidence": "Submit your project repo link before 31/10/26 11:59 PM"
  }
]
```

`time` may be an empty string for an all-day event. Keep this JSON private when it was derived from a real chat.
