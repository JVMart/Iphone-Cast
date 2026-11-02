"""Local document index (SQLite + FTS5). Remembers emails, uploads and web reads
for later search, grouping of near-duplicates, and agent runs."""
import hashlib
import json
import re
import sqlite3
import time

from .harness import HOME

DB = HOME / "index.db"
MAX_TEXT = 200_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY, source TEXT, title TEXT, url TEXT, tag TEXT,
  text TEXT, hash TEXT UNIQUE, added REAL);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(title, text);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY, t REAL, agent TEXT, doc_ids TEXT, backend TEXT,
  question TEXT, output TEXT);
"""


def conn():
    HOME.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def add(source, title, url, text, tag="work"):
    """Index a document. Returns (id, created); exact duplicates are not re-added."""
    text = (text or "").strip()[:MAX_TEXT]
    h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
    with conn() as c:
        row = c.execute("SELECT id FROM documents WHERE hash=?", (h,)).fetchone()
        if row:
            return row["id"], False
        cur = c.execute(
            "INSERT INTO documents(source,title,url,tag,text,hash,added) VALUES(?,?,?,?,?,?,?)",
            (source, title or "(untitled)", url, (tag or "work").strip().lower(), text, h, time.time()))
        c.execute("INSERT INTO docs_fts(rowid,title,text) VALUES(?,?,?)",
                  (cur.lastrowid, title or "", text))
        return cur.lastrowid, True


def list_docs(tag=None, limit=200, source=None, q=None):
    if q and q.strip():
        docs = search(q, limit)
    else:
        with conn() as c:
            docs = [dict(r) for r in c.execute(
                "SELECT * FROM documents ORDER BY added DESC LIMIT ?", (limit,))]
    return [d for d in docs if (not tag or d["tag"] == tag) and (not source or d["source"] == source)]


def sources():
    with conn() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT source FROM documents ORDER BY source")]


def retag(doc_id, tag):
    with conn() as c:
        c.execute("UPDATE documents SET tag=? WHERE id=?",
                  ((tag or "note").strip().lower()[:40], int(doc_id)))


def get(ids):
    ids = [int(i) for i in ids]
    if not ids:
        return []
    with conn() as c:
        q = ",".join("?" * len(ids))
        return [dict(r) for r in c.execute(
            f"SELECT * FROM documents WHERE id IN ({q}) ORDER BY added", ids)]


def delete(doc_id):
    with conn() as c:
        c.execute("DELETE FROM documents WHERE id=?", (int(doc_id),))
        c.execute("DELETE FROM docs_fts WHERE rowid=?", (int(doc_id),))


def tags():
    with conn() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT tag FROM documents ORDER BY tag")]


def search(query, limit=8):
    words = re.findall(r"\w+", (query or "").lower())[:12]
    if not words:
        return []
    fts = " OR ".join(f'"{w}"' for w in words)
    with conn() as c:
        try:
            rows = c.execute(
                "SELECT d.* FROM docs_fts f JOIN documents d ON d.id=f.rowid "
                "WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?", (fts, limit)).fetchall()
        except sqlite3.OperationalError:
            like = f"%{words[0]}%"
            rows = c.execute("SELECT * FROM documents WHERE text LIKE ? LIMIT ?",
                             (like, limit)).fetchall()
        return [dict(r) for r in rows]


def _shingles(text, n=3):
    w = re.findall(r"\w+", text.lower())
    return {tuple(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def similar_groups(docs, threshold=0.5):
    """Group documents whose text overlaps heavily (same/near-same info)."""
    sets = {d["id"]: _shingles(d["text"]) for d in docs}
    parent = {i: i for i in sets}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ids = list(sets)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            sa, sb = sets[ids[a]], sets[ids[b]]
            if sa and sb and len(sa & sb) / len(sa | sb) >= threshold:
                parent[find(ids[a])] = find(ids[b])
    groups = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]


def save_run(agent, doc_ids, backend, question, output):
    with conn() as c:
        c.execute("INSERT INTO runs(t,agent,doc_ids,backend,question,output) VALUES(?,?,?,?,?,?)",
                  (time.time(), agent, json.dumps(list(doc_ids)), backend, question, output))


def list_runs(limit=20, agent=None, q=None):
    with conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM runs ORDER BY t DESC LIMIT 500")]
    ql = (q or "").lower().strip()
    rows = [r for r in rows if (not agent or r["agent"] == agent)
            and (not ql or ql in (r["output"] + " " + (r["question"] or "")).lower())]
    return rows[:limit]
