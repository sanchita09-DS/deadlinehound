# DeadlineHound

Private, local AI that finds possible deadlines and events in exported WhatsApp chats, checks the evidence, and creates a calendar file. The project includes an open-standard Agent Skill and a local web app.

Built for the Hacktoberfest Hack Day: Best Open-Source AI Project.

## The problem

Important announcements can get lost among hundreds of group-chat messages.

## What it does

1. Reads a WhatsApp `.txt` export and filters messages that look like announcements.
2. Asks a local open-weight model for possible events.
3. Checks that the quoted evidence appears in the message and that supported dates and times are valid.
4. Lets you review, edit, and untick events before downloading an `.ics` calendar with reminders.

The model can miss events. Always check the evidence and the original chat before adding calendar events.

## Model and licensing

| Item | Value |
| --- | --- |
| Model | `llama3.2:1b` through Ollama |
| Model size | 1 billion parameters; Ollama package is about 1.3 GB |
| Runtime | Ollama local HTTP API; no API key |
| Project code | MIT; see [LICENSE](LICENSE) |
| Model terms | Llama 3.2 has separate [Meta Community License terms](https://dev.meta.ai/llama/llama3_2/license) |

The model is open-weight; that does not mean it is itself open-source software. See [Ollama's Llama 3.2 model page](https://ollama.com/library/llama3.2) for model details.

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- The `llama3.2:1b` model
- Pytest only if you want to run the automated tests

The app and project scripts use Python's standard library. They do not require Streamlit, pandas, or the Ollama Python package.

## Run the app

1. Install [Python](https://www.python.org/downloads/) and [Ollama](https://ollama.com/download).
2. In a terminal, download the model and start DeadlineHound:

   ```powershell
   ollama pull llama3.2:1b
   python app.py
   ```

3. The app opens at `http://127.0.0.1:8765`. If it does not open automatically, enter that address in your browser. Keep the terminal open while using the app; press **Ctrl+C** there to stop it.
4. Upload `sample_data/sample_chat.txt`, choose **Find possible deadlines with local AI**, review and edit the results, then download the `.ics` file.

## Run the parser and calendar scripts

From the project root, list likely announcements in the fictional sample:

```powershell
python skills/chat-deadline-extractor/scripts/parse_chat.py sample_data/sample_chat.txt
```

The parser assumes day/month dates by default. Add `--mdy` if an export uses month/day dates.

To make a calendar from an events JSON file:

```powershell
python skills/chat-deadline-extractor/scripts/make_ics.py chats/events.json chats/deadlines.ics
```

Timed events last one hour; events without a time are all-day. Each event includes a reminder one day before.

## Use as an Agent Skill

The reusable skill is in [`skills/chat-deadline-extractor/`](skills/chat-deadline-extractor/), following the [Agent Skills specification](https://agentskills.io/specification). Its `SKILL.md` explains when to use it, its privacy rules, and how to run the parser and calendar scripts.

## Privacy

The web app listens only on this computer (`127.0.0.1`). Chat text is submitted to the local app and sent to Ollama running locally. It is not sent to a hosted AI service. Keep real chat exports and derived event data private. The repository ignores `chats/`, `.ics`, and chat `.txt` files; only the fictional sample chat is included.

## Tests

Install pytest if needed, then run the six offline tests:

```powershell
python -m pip install pytest
python -m pytest -q
```

The tests use the fictional sample and do not call Ollama or require internet access.

## What this project demonstrates

- Parsing Android and iPhone WhatsApp exports, including multi-line messages.
- Filtering candidate announcements before asking a local model.
- Checking model output against copied evidence and supported dates.
- Human review and editing before creating an iCalendar file.
- A reusable skill with privacy guidance and reference documentation.

## Limitations

- The web app expects day/month dates. The standalone parser supports month/day with `--mdy`.
- Small models can miss or misunderstand announcements; review every event.
- Ambiguous date wording is omitted rather than guessed.
- The model has its own license terms, separate from this MIT-licensed project.
