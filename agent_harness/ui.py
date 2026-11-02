"""Local UI: python -m agent_harness.ui  ->  http://127.0.0.1:8765
Read-only actions only. Bound to localhost, token-protected against other web pages."""
import html
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .harness import CONFIG, HOME, Session, allowed_domains

PORT = 8765
TOKEN = secrets.token_urlsafe(24)
APPS = {
    "Outlook (web)": "https://outlook.office.com/mail",
    "Gmail": "https://mail.google.com",
    "Teams": "https://teams.microsoft.com",
    "Custom": "",
}

HISTORY = HOME / "history.jsonl"
MAX_HISTORY = 50

PAGE = """<!doctype html><meta charset=utf-8><title>Agent harness</title>
<style>
*{{box-sizing:border-box}}
body{{font:15px system-ui,sans-serif;margin:0;color:#1d1b2e;min-height:100vh;
background:linear-gradient(135deg,#ffe3f1,#e0e7ff 45%,#d6f5ec)}}
main{{max-width:900px;margin:0 auto;padding:1.5rem 1rem 4rem}}
h1{{margin:.2rem 0 1rem;font-size:1.7rem;background:linear-gradient(90deg,#7c3aed,#ec4899,#f59e0b);
-webkit-background-clip:text;background-clip:text;color:transparent}}
h2{{margin:2rem 0 .6rem;font-size:1.1rem}}
.panel{{background:#fff;border-radius:16px;padding:1.2rem;box-shadow:0 6px 24px #7c3aed22}}
label{{display:block;font-weight:600;margin:.5rem 0 .2rem}}
input[type=text],select{{width:100%;font:inherit;padding:.55rem .7rem;border:2px solid #e5e7f5;border-radius:10px}}
input:focus,select:focus{{outline:none;border-color:#a78bfa}}
.btns{{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}}
button{{font:inherit;font-weight:600;border:0;color:#fff;padding:.6rem 1.1rem;border-radius:999px;
cursor:pointer;transition:transform .12s,box-shadow .12s}}
button:hover{{transform:translateY(-2px);box-shadow:0 6px 14px #0003}}
.login{{background:linear-gradient(90deg,#7c3aed,#a855f7)}}
.read{{background:linear-gradient(90deg,#ec4899,#f97316)}}
.allow{{background:linear-gradient(90deg,#10b981,#06b6d4)}}
.chips span{{display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:999px;padding:.15rem .7rem;margin:.15rem;font-size:.85rem}}
.msg{{margin:1rem 0;padding:.7rem 1rem;border-radius:12px;background:#fef3c7;font-weight:600}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:1rem}}
.card{{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 16px #0001;
border-top:6px solid hsl(var(--h) 80% 55%);transition:transform .15s}}
.card:hover{{transform:translateY(-3px)}}
.card summary{{list-style:none;cursor:pointer;padding:.9rem 1rem;
background:linear-gradient(160deg,hsl(var(--h) 90% 96%),#fff)}}
.card summary::-webkit-details-marker{{display:none}}
.host{{font-weight:700;color:hsl(var(--h) 60% 35%)}}
.when{{font-size:.8rem;color:#6b7280}}
.snip{{font-size:.85rem;color:#374151;margin-top:.4rem;display:-webkit-box;-webkit-line-clamp:3;
-webkit-box-orient:vertical;overflow:hidden}}
.card[open]{{grid-column:1/-1}}
.card pre{{margin:0;padding:1rem;white-space:pre-wrap;max-height:50vh;overflow:auto;
background:hsl(var(--h) 40% 98%);border-top:1px dashed hsl(var(--h) 60% 80%)}}
.empty{{color:#6b7280}}
</style>
<main>
<h1>Agent browser-session harness</h1>
<form method=post class=panel>
<input type=hidden name=token value="{token}">
<label>App</label><select name=app onchange="u.value=this.value">{apps}</select>
<label>URL</label><input type=text id=u name=url value="{url}" required>
<label>CSS selector (read)</label><input type=text name=selector value="body">
<div class=btns>
<button class=login name=action value=login>1. Log in (opens browser)</button>
<button class=read name=action value=read>2. Read page</button>
<button class=allow name=action value=allow>Allow this domain</button>
</div>
<p class=chips>Allowed: {allowed}</p>
</form>
{msg}{out}
<h2>History</h2>
<div class=cards>{cards}</div>
</main>"""


def _hue(host):
    return sum(ord(c) * (i + 7) for i, c in enumerate(host)) % 360


def save_history(url, text):
    HOME.mkdir(parents=True, exist_ok=True)
    rows = load_history()
    rows.append({"t": time.time(), "url": url, "text": text[:20000]})
    HISTORY.write_text("\n".join(json.dumps(r) for r in rows[-MAX_HISTORY:]) + "\n",
                       encoding="utf-8")


def load_history():
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]


def cards_html():
    cards = []
    for r in reversed(load_history()):
        host = urlparse(r["url"]).hostname or "?"
        when = time.strftime("%b %d, %I:%M %p", time.localtime(r["t"]))
        snip = " ".join(r["text"].split())[:200] or "(empty page - not signed in?)"
        cards.append(
            f'<details class=card style="--h:{_hue(host)}"><summary>'
            f'<div class=host>{html.escape(host)}</div><div class=when>{when}</div>'
            f'<div class=snip>{html.escape(snip)}</div></summary>'
            f'<pre>{html.escape(r["text"])}</pre></details>')
    return "".join(cards) or '<p class=empty>No reads yet. Your past reads will show up here as cards.</p>'


def render(msg="", out="", url=""):
    apps = "".join(f'<option value="{html.escape(v)}">{html.escape(k)}</option>'
                   for k, v in APPS.items())
    chips = "".join(f"<span>{html.escape(d)}</span>" for d in sorted(allowed_domains())) or "none"
    return PAGE.format(token=TOKEN, apps=apps, url=html.escape(url), allowed=chips,
                       msg=f"<div class=msg>{html.escape(msg)}</div>" if msg else "",
                       out="", cards=cards_html())


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
            save_history(url, text)
            self._send(render("Saved to history below.", url=url))
        except Exception as e:
            self._send(render(f"Error: {e}", url=url))


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
