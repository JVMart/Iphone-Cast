"""Local UI: python -m agent_harness.ui  ->  http://127.0.0.1:8765
Agents are read-only. Bound to localhost; a per-run token blocks other web pages."""
import email
import email.policy
import html
import json
import os
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from . import agents, llm, store
from .harness import CONFIG, HOME, Session, allowed_domains

PORT = 8765
TOKEN = secrets.token_urlsafe(24)
MAX_BODY = 8_000_000
CONNS = HOME / "connections.json"
DEFAULT_CONNS = [
    {"name": "Outlook", "url": "https://outlook.office.com/mail", "tag": "work"},
    {"name": "Gmail", "url": "https://mail.google.com", "tag": "work"},
    {"name": "Teams", "url": "https://teams.microsoft.com", "tag": "work"},
]
SUBJECTS = ["work", "procedure", "cooking", "ai", "books", "finance", "health", "travel",
            "learning", "personal", "note"]
AGENT_BUTTONS = [
    ("summarize", "Summarize", "a-sum"),
    ("important", "Flag important", "a-imp"),
    ("synthesize", "Compare & questions", "a-syn"),
]
VIEWS = [("library", "Library"), ("summaries", "Summaries"), ("apps", "Apps"), ("add", "Add")]
SOURCE_LABEL = {"email": "Email", "web": "Web page", "upload": "File / note"}
esc = html.escape

CSS = """
*{box-sizing:border-box}
body{font:15px system-ui,sans-serif;margin:0;color:#1d1b2e;min-height:100vh;
background:linear-gradient(135deg,#ffe3f1,#e0e7ff 45%,#d6f5ec) fixed}
main{max-width:1100px;margin:0 auto;padding:1rem 1rem 7rem}
.bar{position:sticky;top:0;z-index:10;background:#ffffffee;backdrop-filter:blur(8px);
box-shadow:0 2px 14px #7c3aed33;padding:.6rem 1rem}
.bar .in{max-width:1100px;margin:0 auto;display:flex;gap:.8rem;align-items:center;flex-wrap:wrap}
.logo{font-weight:800;font-size:1.15rem;background:linear-gradient(90deg,#7c3aed,#ec4899,#f59e0b);
-webkit-background-clip:text;background-clip:text;color:transparent}
.bar form{flex:1;display:flex;gap:.4rem;min-width:240px}
.bar input[type=text]{flex:1;border-radius:999px;padding:.55rem 1rem}
.tabs{display:flex;gap:.3rem}
.tabs a{padding:.4rem .9rem;border-radius:999px;text-decoration:none;color:#5b21b6;font-weight:600}
.tabs a.on{background:linear-gradient(90deg,#7c3aed,#ec4899);color:#fff}
.pills{display:flex;gap:.35rem;flex-wrap:wrap;margin:.5rem 0 .2rem;align-items:center}
.pills b{font-size:.8rem;color:#6b7280;margin-right:.2rem}
.pills a{padding:.2rem .75rem;border-radius:999px;background:#fff;color:#374151;text-decoration:none;
font-size:.85rem;box-shadow:0 1px 4px #0002}
.pills a.on{background:#7c3aed;color:#fff}
h2{margin:1.5rem 0 .6rem;font-size:1.1rem}
.panel{background:#fff;border-radius:16px;padding:1.2rem;box-shadow:0 6px 24px #7c3aed22;margin-bottom:1rem}
label{display:block;font-weight:600;margin:.5rem 0 .2rem}
input[type=text],select,textarea{width:100%;font:inherit;padding:.55rem .7rem;border:2px solid #e5e7f5;border-radius:10px}
textarea{min-height:90px}
input:focus,select:focus,textarea:focus{outline:none;border-color:#a78bfa}
.row{display:flex;gap:.8rem;flex-wrap:wrap}.row>*{flex:1;min-width:180px}
.btns{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.7rem}
button{font:inherit;font-weight:600;border:0;color:#fff;padding:.5rem 1.1rem;border-radius:999px;
cursor:pointer;transition:transform .12s,box-shadow .12s}
button:hover{transform:translateY(-2px);box-shadow:0 6px 14px #0003}
.login,.a-sum,.go{background:linear-gradient(90deg,#7c3aed,#a855f7)}
.read,.a-imp{background:linear-gradient(90deg,#ec4899,#f97316)}
.allow,.a-syn{background:linear-gradient(90deg,#10b981,#06b6d4)}
.ask{background:linear-gradient(90deg,#3b82f6,#6366f1)}
.del{background:#ef4444;padding:.3rem .8rem;font-size:.8rem}
.chips span{display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:999px;padding:.15rem .7rem;margin:.15rem;font-size:.85rem}
.dup{background:#fef3c7!important;color:#92400e!important}
.msg{margin:1rem 0;padding:.7rem 1rem;border-radius:12px;background:#fef3c7;font-weight:600}
.warn{font-size:.85rem;color:#92400e;margin:.4rem 0}
.result{background:linear-gradient(160deg,#f5f3ff,#fff);border-left:6px solid #7c3aed}
.result pre{white-space:pre-wrap;margin:.4rem 0 0;font:inherit}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}
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
.card form{padding:.5rem 1rem}
.card .mini{display:flex;gap:.4rem;align-items:center}
.card .mini input{padding:.3rem .6rem}
.app{padding:1rem}
.app .host{font-size:1.1rem}
.dock{position:fixed;left:0;right:0;bottom:0;background:#fffffff2;box-shadow:0 -4px 20px #7c3aed33;padding:.6rem 1rem}
.dock .in{max-width:1100px;margin:0 auto}
.dock form{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.dock select,.dock input[type=text]{width:auto;flex:1;min-width:140px;padding:.4rem .6rem}
.dock .warn{margin:0;flex-basis:100%}
.empty{color:#6b7280}
"""

JS = """
async function upload(files){
  const t=document.querySelector('input[name=token]').value;
  const tag=document.getElementById('uptag').value||'work';
  for(const f of files){
    const body=new URLSearchParams({token:t,action:'ingest',tag:tag,title:f.name,text:await f.text(),filename:f.name,view:'add'});
    await fetch('/',{method:'POST',body});
  }
  location.href='/?view=library';
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


def load_conns():
    try:
        return json.loads(CONNS.read_text("utf-8"))
    except (OSError, ValueError):
        return list(DEFAULT_CONNS)


def save_conns(items):
    HOME.mkdir(parents=True, exist_ok=True)
    CONNS.write_text(json.dumps(items, indent=1), "utf-8")


def link(view, **kw):
    q = "&".join(f"{k}={quote(str(v))}" for k, v in {"view": view, **kw}.items() if v)
    return "/?" + q


def pills(label, items, current, make):
    out = [f'<a class="{"on" if not current else ""}" href="{esc(make(""))}">All</a>']
    out += [f'<a class="{"on" if current == i else ""}" href="{esc(make(i))}">{esc(SOURCE_LABEL.get(i, i))}</a>'
            for i in items]
    return f'<div class=pills><b>{label}</b>{"".join(out)}</div>'


def cards_html(docs, dup_ids):
    out = []
    for d in docs:
        host = urlparse(d["url"] or "").hostname or SOURCE_LABEL.get(d["source"], d["source"])
        when = time.strftime("%b %d, %I:%M %p", time.localtime(d["added"]))
        snip = " ".join(d["text"].split())[:200] or "(empty - not signed in?)"
        dup = ' <span class="tag dup">similar</span>' if d["id"] in dup_ids else ""
        out.append(
            f'<div class=card style="--h:{hue(d["tag"])}">'
            f'<label class=sel><input type=checkbox name=ids value={d["id"]} form=af> select</label>'
            f'<details><summary><div class=host>{esc(d["title"][:80])}</div>'
            f'<div class=when>{esc(SOURCE_LABEL.get(d["source"], d["source"]))} &middot; {esc(host)} &middot; {when} '
            f'<span class=tag>{esc(d["tag"])}</span>{dup}</div>'
            f'<div class=snip>{esc(snip)}</div></summary>'
            f'<pre>{esc(d["text"])}</pre>'
            f'<form method=post class=mini><input type=hidden name=token value="{TOKEN}">'
            f'<input type=hidden name=id value={d["id"]}>'
            f'<input type=text name=tag value="{esc(d["tag"])}" list=subjects>'
            f'<button class=allow name=action value=retag>Set subject</button>'
            f'<button class=del name=action value=delete>Delete</button></form>'
            f'</details></div>')
    return "".join(out) or '<p class=empty>Nothing here yet. Use Apps to read a signed-in page, or Add to upload.</p>'


def runs_html(agent="", q=""):
    out = []
    for r in store.list_runs(40, agent or None, q):
        when = time.strftime("%b %d, %I:%M %p", time.localtime(r["t"]))
        label = agents.LABELS.get(r["agent"], r["agent"])
        qq = f" - {esc(r['question'])}" if r["question"] else ""
        out.append(
            f'<div class=card style="--h:{hue(r["agent"])}"><details><summary>'
            f'<div class=host>{label}{qq}</div><div class=when>{when} &middot; model: {esc(r["backend"])} '
            f'&middot; docs {esc(r["doc_ids"])}</div>'
            f'<div class=snip>{esc(r["output"][:200])}</div></summary>'
            f'<pre>{esc(r["output"])}</pre></details></div>')
    return "".join(out) or '<p class=empty>No saved agent results match.</p>'


def apps_html(url=""):
    chips = "".join(f"<span>{esc(d)}</span>" for d in sorted(allowed_domains())) or "none"
    cards = []
    for c in load_conns():
        cards.append(
            f'<div class=card style="--h:{hue(c["name"])}"><form method=post class=app>'
            f'<input type=hidden name=token value="{TOKEN}"><input type=hidden name=url value="{esc(c["url"])}">'
            f'<div class=host>{esc(c["name"])}</div><div class=when>{esc(c["url"])}</div>'
            f'<label>Save reads under subject</label><input type=text name=tag value="{esc(c.get("tag", "work"))}" list=subjects>'
            f'<input type=hidden name=selector value="body"><input type=hidden name=name value="{esc(c["name"])}">'
            f'<div class=btns><button class=login name=action value=login>Log in</button>'
            f'<button class=read name=action value=read>Read &amp; index</button>'
            f'<button class=del name=action value=conn_del>Remove</button></div></form></div>')
    return f"""<h2>Connected apps</h2>
<p class=warn>Log in opens a browser on <b>this PC</b>. You sign in yourself (MFA too); no password is ever stored. Agents only read.</p>
<div class=cards>{"".join(cards)}</div>
<form method=post class=panel style="margin-top:1rem"><input type=hidden name=token value="{TOKEN}">
<b>Add an app</b> <span class=when>(adding it also allows its domain)</span>
<div class=row><div><label>Name</label><input type=text name=name placeholder="e.g. Jira, Workday, Recipes"></div>
<div><label>URL</label><input type=text name=url value="{esc(url)}" placeholder="https://..."></div>
<div><label>Subject</label><input type=text name=tag value="work" list=subjects></div></div>
<div class=btns><button class=allow name=action value=conn_add>Add app</button></div>
<p class=chips>Allowed domains: {chips}</p></form>"""


def add_html():
    return f"""<h2>Add to your library</h2>
<div class=panel><span class=when>.eml, .txt, .md, .html, .csv, .json - pick as many as you like</span>
<div class=row><div><label>Subject</label><input type=text id=uptag value="work" list=subjects></div>
<div><label>Upload files</label><input type=file multiple accept=".eml,.txt,.md,.html,.htm,.csv,.json,.log" onchange="upload(this.files)"></div></div>
<form method=post><input type=hidden name=token value="{TOKEN}"><input type=hidden name=view value=add>
<label>Or paste an email, recipe, procedure, notes...</label>
<input type=text name=title placeholder="Title"><textarea name=text placeholder="Paste text here"></textarea>
<label>Subject</label><input type=text name=tag value="note" list=subjects>
<div class=btns><button class=allow name=action value=ingest>Add to library</button></div></form></div>"""


def dock_html(st):
    btns = "".join(f'<button class="{c}" name=action value="{a}">{t}</button>' for a, t, c in AGENT_BUTTONS)
    return f"""<div class=dock><div class=in><form method=post id=af>
<input type=hidden name=token value="{TOKEN}">
<select name=backend title="Model"><option value=auto>Model: Auto</option>
<option value=ollama>Local Ollama{' (running)' if st['ollama'] else ' (not running)'}</option>
<option value=openai>Your API{' (configured)' if st['openai'] else ' (not configured)'}</option>
<option value=none>No AI (keywords)</option></select>
<input type=text name=question placeholder="Ask a question about selected cards (or the whole library)">
{btns}<button class=ask name=action value=ask>Ask</button>
<label class=warn><input type=checkbox name=consent> I'm permitted to send these documents to my API (needed for "Your API")</label>
</form></div></div>"""


def render(msg="", url="", result=None, view="library", q="", tag="", kind="", agent=""):
    st = llm.status()
    looks_url = re.match(r"https?://\S+$", q.strip() or "")
    tabs = "".join(f'<a class="{"on" if v == view else ""}" href="{link(v)}">{n}</a>' for v, n in VIEWS)
    bar = (f'<div class=bar><div class=in><span class=logo>Agent workspace</span>'
           f'<form method=get><input type=hidden name=view value="{"summaries" if view == "summaries" else "library"}">'
           f'<input type=text name=q value="{esc(q)}" placeholder="Search your library, or paste a URL..."><button class=go>Search</button></form>'
           f'<div class=tabs>{tabs}</div></div></div>')
    body = ""
    if msg:
        body += f'<div class=msg>{esc(msg)}</div>'
    if result:
        body += (f'<div class="panel result"><b>{esc(result["title"])}</b> '
                 f'<span class=when>(model: {esc(result["backend"])})</span>'
                 f'<pre>{esc(result["output"])}</pre></div>')
    if view == "apps":
        body += apps_html(url)
    elif view == "add":
        body += add_html()
    elif view == "summaries":
        body += pills("Agent", list(agents.LABELS), agent, lambda a: link("summaries", agent=a, q=q))
        body += f'<div class=cards>{runs_html(agent, q)}</div>'
    else:
        if looks_url:
            body += (f'<form method=post class=panel><input type=hidden name=token value="{TOKEN}">'
                     f'<input type=hidden name=url value="{esc(q.strip())}"><input type=hidden name=selector value=body>'
                     f'<b>{esc(q.strip())}</b><div class=row><div><label>Subject</label>'
                     f'<input type=text name=tag value="work" list=subjects></div></div><div class=btns>'
                     f'<button class=allow name=action value=allow>Allow domain</button>'
                     f'<button class=login name=action value=login>Log in</button>'
                     f'<button class=read name=action value=read>Read &amp; index</button></div></form>')
            docs = []
        else:
            docs = store.list_docs(tag or None, 200, kind or None, q)
        everything = store.list_docs(None, 200)
        counts = {}
        for d in everything:
            counts[d["tag"]] = counts.get(d["tag"], 0) + 1
        subj = sorted(counts, key=lambda t: -counts[t])
        body += pills("Subject", subj, tag, lambda t: link("library", tag=t, kind=kind, q=q))
        body += pills("Type", store.sources(), kind, lambda k: link("library", tag=tag, kind=k, q=q))
        dups = {i for g in store.similar_groups(docs) for i in g}
        body += f'<h2>{len(docs)} item(s)</h2><div class=cards>{cards_html(docs, dups)}</div>'
    dock = dock_html(st) if view == "library" else ""
    subjects = "".join(f"<option>{esc(s)}" for s in sorted(set(SUBJECTS) | set(store.tags())))
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Agent workspace</title><style>{CSS}</style>{bar}<main>{body}</main>{dock}"
            f"<datalist id=subjects>{subjects}</datalist>"
            f'<input type=hidden name=token value="{TOKEN}" form=none><script>{JS}</script>')


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
        host = self.headers.get("Host", "")
        if host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
            return True
        # Private Tailscale access: set HARNESS_TAILNET_HOST to your machine's .ts.net name.
        extra = os.environ.get("HARNESS_TAILNET_HOST", "").strip().lower()
        return bool(extra) and host.lower() == extra

    def do_GET(self):
        if not self._host_ok():
            return self._send("bad host", 403)
        p = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        self._send(render(view=p.get("view", "library"), q=p.get("q", ""), tag=p.get("tag", ""),
                          kind=p.get("kind", ""), agent=p.get("agent", "")))

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
            self._send(render(f"Error: {e}", url=url, view="apps" if url else "library"))

    def _dispatch(self, action, url, get, f):
        if action == "ingest":
            fn = get("filename")
            title, text = parse_upload(fn or get("title") or "pasted", get("text"))
            if not fn and get("title"):
                title = get("title")
            if not text.strip():
                return render("Nothing to add - the text was empty.", view="add")
            src = "email" if fn.lower().endswith(".eml") else "upload"
            _, created = store.add(src, title, "", text, get("tag", "note"))
            return render(f"Added '{title}'." if created else "Already in library (identical text).", view="add")
        if action == "delete":
            store.delete(get("id"))
            return render("Deleted.")
        if action == "retag":
            store.retag(get("id"), get("tag"))
            return render("Subject updated.")
        if action in ("summarize", "important", "synthesize", "ask"):
            return self._agent(action, get, f)
        if action == "conn_del":
            save_conns([c for c in load_conns() if c["url"] != url])
            return render("App removed.", view="apps")

        host = (urlparse(url).hostname or "").lower()
        if urlparse(url).scheme not in ("http", "https") or not host:
            return render("Enter a full http(s) URL.", url=url, view="apps")
        if action == "conn_add":
            name = get("name").strip() or host
            conns = [c for c in load_conns() if c["url"] != url]
            conns.append({"name": name[:40], "url": url, "tag": get("tag", "work") or "work"})
            save_conns(conns)
            if host not in allowed_domains():
                with CONFIG.open("a") as fh:
                    fh.write(f"\n{host}\n")
            return render(f"Added {name} and allowed {host}.", view="apps")
        if action == "allow":
            with CONFIG.open("a") as fh:
                fh.write(f"\n{host}\n")
            return render(f"Allowed {host}", q=url)
        if action == "login":
            if not any(host == d or host.endswith("." + d) for d in allowed_domains()):
                raise PermissionError(f"Click 'Allow domain' for {host} first")
            s = Session(headless=False)
            s.goto(url)
            try:
                s.page.wait_for_event("close", timeout=600000)
            except Exception:
                pass
            s.close()
            return render("Browser closed. Session saved.", view="apps")
        s = Session(headless=True)
        try:
            s.goto(url)
            title = s.page.title() or host
            text = s.read_text(get("selector") or "body")
        finally:
            s.close()
        _, created = store.add("web", title, url, text, get("tag", "work") or "work")
        return render("Read and added to your library." if created else "Page unchanged - already in library.")

    def _agent(self, name, get, f):
        backend, question = get("backend", "auto"), get("question").strip()
        ids = f.get("ids", [])
        docs = store.get(ids)
        if name == "ask":
            if not question:
                return render("Type a question first.")
            docs = docs or store.search(question)
        elif not docs:
            return render("Select at least one card first.")
        if llm.resolve(backend) == "openai" and not get("consent"):
            return render("Tick the permission box before sending documents to your API.")
        if not docs:
            return render("Nothing relevant found in the library.")
        out, used = agents.run(name, docs, question, backend)
        store.save_run(name, [d["id"] for d in docs], used, question, out)
        return render(result={"title": agents.LABELS[name], "output": out, "backend": used})


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
