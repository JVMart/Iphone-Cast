"""Local UI: python -m agent_harness.ui  ->  http://127.0.0.1:8765
Read-only actions only. Bound to localhost, token-protected against other web pages."""
import html
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .harness import CONFIG, Session, allowed_domains

PORT = 8765
TOKEN = secrets.token_urlsafe(24)
APPS = {
    "Outlook (web)": "https://outlook.office.com/mail",
    "Gmail": "https://mail.google.com",
    "Teams": "https://teams.microsoft.com",
    "Custom": "",
}

PAGE = """<!doctype html><meta charset=utf-8><title>Agent harness</title>
<style>body{{font:15px system-ui;max-width:820px;margin:2rem auto;padding:0 1rem}}
input,select,button{{font:inherit;padding:.4rem;margin:.2rem 0}}input[type=text]{{width:100%}}
pre{{background:#f4f4f4;padding:1rem;white-space:pre-wrap;max-height:50vh;overflow:auto}}</style>
<h2>Agent browser-session harness</h2>
<form method=post>
<input type=hidden name=token value="{token}">
<label>App <select name=app onchange="u.value=this.value">{apps}</select></label>
<label>URL<input type=text id=u name=url value="{url}" required></label>
<label>CSS selector (read) <input type=text name=selector value="body"></label>
<button name=action value=login>1. Log in (opens browser)</button>
<button name=action value=read>2. Read page</button>
<button name=action value=allow>Allow this domain</button>
</form>
<p>Allowed: {allowed}</p>
<p><b>{msg}</b></p>{out}"""


def render(msg="", out="", url=""):
    apps = "".join(f'<option value="{html.escape(v)}">{html.escape(k)}</option>'
                   for k, v in APPS.items())
    return PAGE.format(token=TOKEN, apps=apps, url=html.escape(url),
                       allowed=html.escape(", ".join(sorted(allowed_domains())) or "none"),
                       msg=html.escape(msg), out=f"<pre>{html.escape(out)}</pre>" if out else "")


class H(BaseHTTPRequestHandler):
    def _send(self, body, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def _host_ok(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def do_GET(self):
        self._send(render() if self._host_ok() else "bad host", 200 if self._host_ok() else 403)

    def do_POST(self):
        # Playwright's sync API needs a clean thread per action
        out = {}
        t = threading.Thread(target=lambda: out.setdefault("r", self._post()))
        t.start()
        t.join()

    def _post(self):
        if not self._host_ok():
            return self._send("bad host", 403)
        n = int(self.headers.get("Content-Length", 0))
        f = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if not secrets.compare_digest(f.get("token", ""), TOKEN):
            return self._send("bad token", 403)
        url, action = f.get("url", "").strip(), f.get("action")
        host = (urlparse(url).hostname or "").lower()
        if urlparse(url).scheme not in ("http", "https") or not host:
            return self._send(render("Enter a full http(s) URL.", url=url))
        try:
            if action == "allow":
                with CONFIG.open("a") as fh:
                    fh.write(f"\n{host}\n")
                return self._send(render(f"Allowed {host}", url=url))
            if action == "login":
                if host not in allowed_domains():
                    raise PermissionError(f"Click 'Allow this domain' for {host} first")
                s = Session(headless=False)
                s.goto(url)
                input_msg = "Browser opened. Sign in, then close the browser window."
                try:
                    s.page.wait_for_event("close", timeout=600000)
                except Exception:
                    pass
                s.close()
                return self._send(render(input_msg + " Session saved.", url=url))
            s = Session(headless=True)
            try:
                s.goto(url)
                text = s.read_text(f.get("selector") or "body")
            finally:
                s.close()
            self._send(render("Page text:", text[:20000], url))
        except Exception as e:
            self._send(render(f"Error: {e}", url=url))


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
