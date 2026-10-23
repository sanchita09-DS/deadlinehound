"""Small local web app for DeadlineHound; uses only Python's standard library."""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import webbrowser

from deadlinehound.engine import extract_events, make_ics, parse_chat

HOST = "127.0.0.1"
PORT = 8765
MAX_CHAT_BYTES = 2 * 1024 * 1024

PAGE_STYLE = """
<style>
body{font-family:system-ui,Segoe UI,sans-serif;max-width:920px;margin:36px auto;padding:0 18px;color:#172033;background:#f6f8fb}
h1{margin-bottom:4px;color:#183b56}p{line-height:1.5}.card{background:white;border:1px solid #dce3eb;border-radius:12px;padding:20px;margin:18px 0;box-shadow:0 2px 8px #1231}
textarea{width:100%;box-sizing:border-box;min-height:220px;margin:12px 0;padding:12px;border:1px solid #aab7c4;border-radius:8px;font:14px ui-monospace,monospace}
button{background:#176b87;color:white;border:0;border-radius:8px;padding:11px 16px;font-size:15px;cursor:pointer}button:hover{background:#10566d}
input[type=file]{display:block;margin:12px 0}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce3eb}th{background:#edf3f7}.notice{padding:12px;background:#eaf6ee;border-radius:8px}.error{padding:12px;background:#fff0ee;border-radius:8px;color:#8d241b}.muted{color:#526272;font-size:14px}
</style>"""


def page(content: str) -> bytes:
    document = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>DeadlineHound</title>" + PAGE_STYLE + "<body>"
        "<h1>DeadlineHound</h1>"
        "<p>Find possible deadlines in a WhatsApp export, check the evidence, and make a calendar file.</p>"
        + content
        + "</body></html>"
    )
    return document.encode("utf-8")


def home(message: str = "") -> bytes:
    alert = f"<div class='error'>{html.escape(message)}</div>" if message else ""
    content = (
        alert
        + "<section class='card'><h2>1. Choose your chat export</h2>"
        "<p class='muted'>Choose a WhatsApp .txt export. The file is read by this page and sent only to the local DeadlineHound app and Ollama on this computer.</p>"
        "<input id='file' type='file' accept='.txt,text/plain'>"
        "<form method='post' action='/extract'>"
        "<label for='chat'><strong>Chat text</strong></label>"
        "<textarea id='chat' name='chat' required placeholder='Choose a .txt file above, or paste chat text here.'></textarea>"
        "<button type='submit'>Find possible deadlines with local AI</button></form></section>"
        "<p class='muted'>The model suggests events. Python checks that each quote appears in the original message. Review results before adding them to your calendar.</p>"
        "<script>document.getElementById('file').addEventListener('change',async e=>{const f=e.target.files[0];if(f){document.getElementById('chat').value=await f.text();}});</script>"
    )
    return page(content)


def results_page(events: list[dict], parsed_count: int, candidate_count: int, original_chat: str) -> bytes:
    summary = (
        f"<p class='notice'>Read {parsed_count} messages; {candidate_count} looked like possible announcements; "
        f"{len(events)} event(s) passed the evidence and date checks.</p>"
    )
    if events:
        rows = []
        for index, event in enumerate(events):
            rows.append(
                "<tr><td><input type='checkbox' name='keep_" + str(index)
                + "' value='1' checked aria-label='Keep event'></td><td><input required name='title_"
                + str(index) + "' value='" + html.escape(event["title"], quote=True)
                + "'></td><td><input required type='date' name='date_" + str(index)
                + "' value='" + html.escape(event["date"], quote=True)
                + "'><br><input type='time' name='time_" + str(index) + "' value='"
                + html.escape(event["time"], quote=True) + "'></td><td><input name='action_"
                + str(index) + "' value='" + html.escape(event["action"], quote=True)
                + "'></td><td><q>" + html.escape(event["evidence"]) + "</q></td></tr>"
            )
        table = (
            "<p>Edit the title, date, or time, and untick any event you do not want.</p>"
            "<form method='post' action='/calendar'><input type='hidden' name='count' value='"
            + str(len(events)) + "'><div style='overflow:auto'><table><thead><tr>"
            "<th>Keep</th><th>Event</th><th>Date and time</th><th>Action</th>"
            "<th>Evidence from the message</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<button type='submit'>Download selected events (.ics)</button></form>"
        )
    else:
        table = "<p>No event passed the checks. Review the chat wording or try a larger model; don't invent a deadline.</p>"
        export = ""
    again = "<p><a href='/'>Analyze another chat</a></p>"
    # Retain the original chat in this response only for a clear review trail; it is never logged or sent off-device.
    source_note = "<details><summary>Show the submitted chat</summary><pre style='white-space:pre-wrap'>" + html.escape(original_chat) + "</pre></details>"
    return page("<section class='card'><h2>2. Review the results</h2>" + summary + table + source_note + again + "</section>")


class Handler(BaseHTTPRequestHandler):
    def _send(
        self,
        data: bytes,
        content_type: str = "text/html; charset=utf-8",
        status: int = 200,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        self._send(home())

    def do_POST(self) -> None:
        if self.path not in ("/extract", "/calendar"):
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        if size <= 0 or size > MAX_CHAT_BYTES + 200_000:
            self._send(home("The submitted content is empty or too large (maximum 2 MB)."), status=413)
            return
        form = parse_qs(self.rfile.read(size).decode("utf-8", errors="replace"), keep_blank_values=True)
        if self.path == "/extract":
            chat_text = form.get("chat", [""])[0]
            messages = parse_chat(chat_text)
            if not messages:
                self._send(home("I couldn't read messages in this text. Check that it is a WhatsApp .txt export in day/month format."))
                return
            try:
                events, candidate_count = extract_events(messages)
            except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                self._send(home(str(exc)))
                return
            self._send(results_page(events, len(messages), candidate_count, chat_text))
            return
        try:
            count = int(form.get("count", ["0"])[0])
            if count < 0 or count > 100:
                raise ValueError("Invalid event list")
            events = []
            for index in range(count):
                if form.get(f"keep_{index}", [""])[0] != "1":
                    continue
                events.append(
                    {
                        "title": form.get(f"title_{index}", [""])[0].strip(),
                        "date": form.get(f"date_{index}", [""])[0].strip(),
                        "time": form.get(f"time_{index}", [""])[0].strip(),
                        "action": form.get(f"action_{index}", [""])[0].strip(),
                    }
                )
            if not events:
                self._send(home("Select at least one event to include in the calendar."))
                return
            data = make_ics(events)
        except (ValueError, TypeError, json.JSONDecodeError):
            self._send(home("The calendar data was not valid. Please analyze the chat again."))
            return
        self._send(
            data,
            "text/calendar; charset=utf-8",
            extra_headers=(("Content-Disposition", 'attachment; filename="deadlines.ics"'),),
        )

    def log_message(self, format: str, *args) -> None:
        # Keep server logs free of message contents; only the local request path is logged.
        super().log_message(format, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"DeadlineHound is running locally at {url}. Press Ctrl+C to stop it.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeadlineHound stopped.")
    finally:
        server.server_close()
