"""Local UI: python -m agent_harness.ui  ->  http://127.0.0.1:8765
Agents are read-only. Bound to localhost; a per-run token blocks other web pages."""
import email
import email.policy
import html
import json
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import agents, llm, store
from .harness import CONFIG, Session, allowed_domains

PORT = 8765
TOKEN = secrets.token_urlsafe(24)
MAX_BODY = 8_000_000
APPS = {
    "Outlook (web)": "https://outlook.office.com/mail",
    "Gmail": "https://mail.google.com",
    "Teams": "https://teams.microsoft.com",
    "Custom": "",
}
AGENT_BUTTONS = [
    ("summarize", "Summarize", "a-sum"),
    ("important", "Flag important", "a-imp"),
    ("synthesize", "Compare & questions", "a-syn"),
]
esc = html.escape

CSS = """
*{box-sizing:border-box}
body{font:15px system-ui,sans-serif;margin:0;color:#1d1b2e;min-height:100vh;
background:linear-gradient(135deg,#ffe3f1,#e0e7ff 45%,#d6f5ec)}
main{max-width:1000px;margin:0 auto;padding:1.5rem 1rem 4rem}
h1{margin:.2rem 0 1rem;font-size:1.7rem;background:linear-gradient(90deg,#7c3aed,#ec4899,#f59e0b);
-webkit-background-clip:text;background-clip:text;color:transparent}
h2{margin:2rem 0 .6rem;font-size:1.1rem}
.panel{background:#fff;border-radius:16px;padding:1.2rem;box-shadow:0 6px 24px #7c3aed22;margin-bottom:1rem}
label{display:block;font-weight:600;margin:.5rem 0 .2rem}
input[type=text],select,textarea{width:100%;font:inherit;padding:.55rem .7rem;border:2px solid #e5e7f5;border-radius:10px}
textarea{min-height:90px}
input:focus,select:focus,textarea:focus{outline:none;border-color:#a78bfa}
.row{display:flex;gap:.8rem;flex-wrap:wrap}.row>*{flex:1;min-width:180px}
.btns{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.9rem}
button{font:inherit;font-weight:600;border:0;color:#fff;padding:.55rem 1.1rem;border-radius:999px;
cursor:pointer;transition:transform .12s,box-shadow .12s}
button:hover{transform:translateY(-2px);box-shadow:0 6px 14px #0003}
.login,.a-sum{background:linear-gradient(90deg,#7c3aed,#a855f7)}
.read,.a-imp{background:linear-gradient(90deg,#ec4899,#f97316)}
.allow,.a-syn{background:linear-gradient(90deg,#10b981,#06b6d4)}
.ask{background:linear-gradient(90deg,#3b82f6,#6366f1)}
.del{background:#ef4444;padding:.3rem .8rem;font-size:.8rem}
.chips span{display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:999px;padding:.15rem .7rem;margin:.15rem;font-size:.85rem}
.dup{background:#fef3c7!important;color:#92400e!important}
.msg{margin:1rem 0;padding:.7rem 1rem;border-radius:12px;background:#fef3c7;font-weight:600}
.warn{font-size:.85rem;color:#92400e;margin:.4rem 0}
.result{background:linear-gradient(160deg,#f5f3ff,#fff);border-left:6px solid #7c3aed}
.result pre{white-space:pre-wrap;margin:.4rem 0 0}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:1rem}
.card{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 16px #0001;
border-top:6px solid hsl(var(--h) 80% 55%);transition:transform .15s}
.card:hover{transform:translateY(-3px)}
.card:has(details[open]){grid-column:1/-1}
.sel{display:flex;gap:.4rem;align-items:center;margin:0;padding:.5rem 1rem 0;font-size:.85rem;font-weight:600}
.card summary{list-style:none;cursor:pointer;padding:.4rem 1rem .9rem}
.card summary::-webkit-details-marker{display:none}
.host{font-weight:700;color:hsl(var(--h) 60% 35%)}
.when{font-size:.8rem;color:#6b7280}
.tag{display:inline-block;background:hsl(var(--h) 80% 92%);color:hsl(var(--h) 60% 30%);border-radius:999px;padding:0 .6rem;font-size:.75rem}
.snip{font-size:.85rem;color:#374151;margin-top:.4rem;display:-webkit-box;-webkit-line-clamp:3;
-webkit-box-orient:vertical;overflow:hidden}
.card pre{margin:0;padding:1rem;white-space:pre-wrap;max-height:50vh;overflow:auto;
background:hsl(var(--h) 40% 98%);border-top:1px dashed hsl(var(--h) 60% 80%)}
.card form{padding:.6rem 1rem}
.empty{color:#6b7280}
"""

JS = """
async function upload(files){
  const t=document.querySelector('input[name=token]').value;
  const tag=document.getElementById('uptag').value||'work';
  for(const f of files){
    const body=new URLSearchParams({token:t,action:'ingest',tag:tag,title:f.name,text:await f.text(),filename:f.name});
    await fetch('/',{method:'POST',body});
  }
  location.reload();
}
"""


def hue(s):
    return sum(ord(c) * (i + 7) for i, c in enumerate(s)) % 360


def clean_html(t):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def parse_upload(name, raw):
    low = name.lower()
    if low.endswith(".eml"):
        msg = email.message_from_string(raw, policy=email.policy.default)
        body = msg.get_body(("plain", "html"))
        text = body.get_content() if body else ""
        if body is not None and body.get_content_type() == "text/html":
            text = clean_html(text)
        head = f"From: {msg['from']}\nTo: {msg['to']}\nDate: {msg['date']}\n\n"
        return str(msg["subject"] or name), head + text
    if low.endswith((".html", ".htm")):
        return name, clean_html(raw)
    return name, raw


def cards_html(docs, dup_ids):
    out = []
    for d in docs:
        host = urlparse(d["url"] or "").hostname or d["source"]
        when = time.strftime("%b %d, %I:%M %p", time.localtime(d["added"]))
        snip = " ".join(d["text"].split())[:200] or "(empty - not signed in?)"
        dup = ' <span class="tag dup">similar</span>' if d["id"] in dup_ids else ""
        out.append(
            f'<div class=card style="--h:{hue(host)}">'
            f'<label class=sel><input type=checkbox name=ids value={d["id"]} form=af> select</label>'
            f'<details><summary><div class=host>{esc(d["title"][:80])}</div>'
            f'<div class=when>{esc(host)} &middot; {when} <span class=tag>{esc(d["tag"])}</span>{dup}</div>'
            f'<div class=snip>{esc(snip)}</div></summary>'
            f'<pre>{esc(d["text"])}</pre>'
            f'<form method=post><input type=hidden name=token value="{TOKEN}">'
            f'<input type=hidden name=id value={d["id"]}>'
            f'<button class=del name=action value=delete>Delete from index</button></form>'
            f'</details></div>')
    return "".join(out) or '<p class=empty>Nothing indexed yet. Read a page, upload files, or paste text above.</p>'


def runs_html():
    out = []
    for r in store.list_runs(8):
        when = time.strftime("%b %d, %I:%M %p", time.localtime(r["t"]))
        label = agents.LABELS.get(r["agent"], r["agent"])
        q = f" - {esc(r['question'])}" if r["question"] else ""
        out.append(
            f'<div class=card style="--h:{hue(r["agent"])}"><details><summary>'
            f'<div class=host>{label}{q}</div><div class=when>{when} &middot; model: {esc(r["backend"])} '
            f'&middot; docs {esc(r["doc_ids"])}</div>'
            f'<div class=snip>{esc(r["output"][:200])}</div></summary>'
            f'<pre>{esc(r["output"])}</pre></details></div>')
    return "".join(out) or '<p class=empty>Agent results are remembered here for reference.</p>'


def render(msg="", url="", result=None, tag=""):
    apps = "".join(f'<option value="{esc(v)}">{esc(k)}</option>' for k, v in APPS.items())
    chips = "".join(f"<span>{esc(d)}</span>" for d in sorted(allowed_domains())) or "none"
    st = llm.status()
    docs = store.list_docs(tag or None)
    dups = {i for g in store.similar_groups(docs) for i in g}
    tag_opts = "".join(f'<option value="{esc(t)}"{" selected" if t == tag else ""}>{esc(t)}</option>'
                       for t in store.tags())
    res = ""
    if result:
        res = (f'<div class="panel result"><b>{esc(result["title"])}</b> '
               f'<span class=when>(model: {esc(result["backend"])})</span>'
               f'<pre>{esc(result["output"])}</pre></div>')
    btns = "".join(f'<button class="{c}" name=action value="{a}">{t}</button>' for a, t, c in AGENT_BUTTONS)
    return f"""<!doctype html><meta charset=utf-8><title>Agent harness</title><style>{CSS}</style>
<main><h1>Agent workspace</h1>{f'<div class=msg>{esc(msg)}</div>' if msg else ''}
<form method=post class=panel>
<input type=hidden name=token value="{TOKEN}">
<b>1. Connect an app</b>
<label>App</label><select name=app onchange="u.value=this.value">{apps}</select>
<label>URL</label><input type=text id=u name=url value="{esc(url)}">
<label>CSS selector (read)</label><input type=text name=selector value="body">
<div class=btns>
<button class=login name=action value=login>Log in (opens browser)</button>
<button class=read name=action value=read>Read page &amp; index it</button>
<button class=allow name=action value=allow>Allow this domain</button></div>
<p class=chips>Allowed: {chips}</p></form>

<div class=panel><b>2. Add documents</b> <span class=when>(.eml, .txt, .md, .html, .csv - you can pick many)</span>
<div class=row><div><label>Tag</label><input type=text id=uptag value="work" list=taglist></div>
<div><label>Upload files</label><input type=file multiple accept=".eml,.txt,.md,.html,.htm,.csv,.json,.log" onchange="upload(this.files)"></div></div>
<datalist id=taglist><option>work<option>procedure<option>note<option>personal</datalist>
<form method=post><input type=hidden name=token value="{TOKEN}">
<label>Or paste an email / procedure to remember</label>
<input type=text name=title placeholder="Title">
<textarea name=text placeholder="Paste text here"></textarea>
<input type=hidden name=tag value="work">
<div class=btns><button class=allow name=action value=ingest>Add to index</button></div></form></div>

<form method=post id=af class=panel><input type=hidden name=token value="{TOKEN}">
<b>3. Ask the agents</b>
<div class=row><div><label>Model</label><select name=backend>
<option value=auto>Auto (local Ollama if running, else keyword mode)</option>
<option value=ollama>Local Ollama{' - running' if st['ollama'] else ' - not running'}</option>
<option value=openai>Your API{' - configured' if st['openai'] else ' - not configured (set HARNESS_LLM_* env vars)'}</option>
<option value=none>No AI (keyword mode)</option></select></div>
<div><label>Question (for Ask)</label><input type=text name=question placeholder="e.g. What did finance say about the Q3 invoice?"></div></div>
<label class=warn><input type=checkbox name=consent> I'm permitted to send the selected documents to my API (required for "Your API")</label>
<p class=warn>Select documents below, then pick an agent. Ask with nothing selected searches the whole index.</p>
<div class=btns>{btns}<button class=ask name=action value=ask>Ask</button></div></form>
{res}
<h2>Remembered agent results</h2><div class=cards>{runs_html()}</div>
<h2>Index</h2>
<form method=post class=panel><input type=hidden name=token value="{TOKEN}"><div class=row>
<div><label>Filter by tag</label><select name=tag><option value="">All</option>{tag_opts}</select></div>
<div><button class=allow name=action value=filter style="margin-top:1.7rem">Filter</button></div></div></form>
<div class=cards>{cards_html(docs, dups)}</div></main><script>{JS}</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def do_GET(self):
        if not self._host_ok():
            return self._send("bad host", 403)
        self._send(render())

    def do_POST(self):
        # Playwright's sync API needs a clean thread per action
        t = threading.Thread(target=self._post)
        t.start()
        t.join()

    def _post(self):
        if not self._host_ok():
            return self._send("bad host", 403)
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_BODY:
            return self._send("too large", 413)
        f = parse_qs(self.rfile.read(n).decode("utf-8", "replace"), keep_blank_values=True)
        get = lambda k, d="": f.get(k, [d])[0]
        if not secrets.compare_digest(get("token"), TOKEN):
            return self._send("bad token", 403)
        action, url = get("action"), get("url").strip()
        try:
            self._send(self._dispatch(action, url, get, f))
        except Exception as e:
            self._send(render(f"Error: {e}", url=url))

    def _dispatch(self, action, url, get, f):
        if action == "ingest":
            title, text = parse_upload(get("filename") or get("title") or "pasted", get("text"))
            if get("filename") == "" and get("title"):
                title = get("title")
            if not text.strip():
                return render("Nothing to add - the text was empty.")
            _, created = store.add("upload", title, "", text, get("tag", "work"))
            return render(f"Added '{title}'." if created else "Already indexed (identical text).")
        if action == "delete":
            store.delete(get("id"))
            return render("Deleted from index.")
        if action == "filter":
            return render(tag=get("tag"))
        if action in ("summarize", "important", "synthesize", "ask"):
            return self._agent(action, get, f)

        host = (urlparse(url).hostname or "").lower()
        if urlparse(url).scheme not in ("http", "https") or not host:
            return render("Enter a full http(s) URL.", url=url)
        if action == "allow":
            with CONFIG.open("a") as fh:
                fh.write(f"\n{host}\n")
            return render(f"Allowed {host}", url=url)
        if action == "login":
            if not any(host == d or host.endswith("." + d) for d in allowed_domains()):
                raise PermissionError(f"Click 'Allow this domain' for {host} first")
            s = Session(headless=False)
            s.goto(url)
            try:
                s.page.wait_for_event("close", timeout=600000)
            except Exception:
                pass
            s.close()
            return render("Browser closed. Session saved.", url=url)
        s = Session(headless=True)
        try:
            s.goto(url)
            title = s.page.title() or host
            text = s.read_text(get("selector") or "body")
        finally:
            s.close()
        _, created = store.add("web", title, url, text, "work")
        return render("Read and indexed." if created else "Page unchanged - already indexed.", url=url)

    def _agent(self, name, get, f):
        backend, question = get("backend", "auto"), get("question").strip()
        ids = f.get("ids", [])
        docs = store.get(ids)
        if name == "ask":
            if not question:
                return render("Type a question first.")
            docs = docs or store.search(question)
        elif not docs:
            return render("Select at least one document first.")
        if llm.resolve(backend) == "openai" and not get("consent"):
            return render("Tick the permission box before sending documents to your API.")
        if not docs:
            return render("Nothing relevant found in the index.")
        out, used = agents.run(name, docs, question, backend)
        store.save_run(name, [d["id"] for d in docs], used, question, out)
        return render(result={"title": agents.LABELS[name], "output": out, "backend": used})


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
