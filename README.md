# DeadlineHound

DeadlineHound is an early local prototype for finding deadline and meeting announcements in exported WhatsApp chats. A small open-weight language model proposes events; Python checks that the quoted evidence exists in the original message and rejects invalid or past dates. You can review the results and download an `.ics` calendar file.

This version uses Python's standard library and Ollama's local HTTP API. It does not use Streamlit, pandas, the Ollama Python package, an API key, or a cloud AI service. That keeps it usable on systems where compiled Python packages are blocked.

## Current status

The local web prototype is being built. It supports common day/month Android and iPhone WhatsApp text exports. It is not yet a finished Agent Skill; the `skills/` folder will be completed separately.

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- The `llama3.2:1b` model (or update `MODEL` in `deadlinehound/engine.py`)

The model is open-weight under Meta's Llama terms. Open-weight does not mean that the model is itself open-source software. The project code is separately licensed under MIT; see [LICENSE](LICENSE) and the [Llama 3.2 license](https://www.llama.com/llama3_2/license/).

## Run locally

In a terminal opened at the project root:

```powershell
ollama pull llama3.2:1b
python app.py
```

The app opens at `http://127.0.0.1:8765`. If the browser does not open automatically, copy that address into your browser. Keep the terminal open while using the app; press `Ctrl+C` in that terminal to stop it.

No `pip install` step is needed. `requirements.txt` is intentionally empty of third-party packages because this prototype uses only Python's built-in modules.

## Privacy

The app listens only on this computer at `127.0.0.1`. A selected text file is read in the browser and submitted to the local app; candidate messages are sent to Ollama at `127.0.0.1:11434`. No chat is sent to a hosted AI service. Do not commit real chat exports: `.gitignore` ignores `.txt`, `.zip`, and `.ics` files, with an exception reserved for a fictional sample chat.

## Limitations

- The parser expects day/month WhatsApp date formats.
- Small models can miss, misunderstand, or omit events. Always check the original message and the event date before importing the calendar.
- Relative dates and unusual chat export formats may not be interpreted correctly.

## License

The DeadlineHound code is MIT licensed. The model is subject to Meta's separate Llama terms linked above.
