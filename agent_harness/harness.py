"""Browser-session harness: you sign in manually (incl. MFA); an agent reuses
that session with an allowlist, read-only default, per-action confirmation
for writes, and an audit log. No passwords are ever stored or handled."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "agent_harness"
PROFILE = HOME / "profile"
AUDIT = HOME / "audit.jsonl"
CONFIG = Path(__file__).with_name("allowed_domains.txt")


def allowed_domains():
    if not CONFIG.exists():
        return set()
    return {l.strip().lower() for l in CONFIG.read_text().splitlines()
            if l.strip() and not l.startswith("#")}


def audit(action, **detail):
    HOME.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), "action": action, **detail}) + "\n")


class Session:
    def __init__(self, headless=True, allow_write=False, confirm=input):
        self.allow_write = allow_write
        self.confirm = confirm
        self._pw = sync_playwright().start()
        PROFILE.mkdir(parents=True, exist_ok=True)
        try:
            self.ctx = self._pw.chromium.launch_persistent_context(
                str(PROFILE), headless=headless)
        except Exception:
            self._pw.stop()
            raise
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()

    def close(self):
        self.ctx.close()
        self._pw.stop()

    def _check_url(self, url):
        host = (urlparse(url).hostname or "").lower()
        ok = any(host == d or host.endswith("." + d) for d in allowed_domains())
        if not ok:
            audit("blocked", url=url)
            raise PermissionError(f"{host} not in allowed_domains.txt")

    # --- read-only actions ---
    def goto(self, url):
        self._check_url(url)
        audit("goto", url=url)
        self.page.goto(url)
        self._check_url(self.page.url)

    def read_text(self, selector="body"):
        self._check_url(self.page.url)
        audit("read", url=self.page.url, selector=selector)
        return self.page.inner_text(selector)

    def screenshot(self, path):
        self._check_url(self.page.url)
        audit("screenshot", url=self.page.url)
        self.page.screenshot(path=path, full_page=True)

    # --- write actions: need allow_write AND a human yes each time ---
    def _gate(self, desc):
        self._check_url(self.page.url)
        if not self.allow_write:
            audit("write_denied", desc=desc)
            raise PermissionError("write actions disabled (use --allow-write)")
        if self.confirm(f"Agent wants to: {desc}. Allow? [y/N] ").strip().lower() != "y":
            audit("write_rejected", desc=desc)
            raise PermissionError("rejected by user")
        audit("write", url=self.page.url, desc=desc)

    def click(self, selector):
        self._gate(f"click {selector}")
        self.page.click(selector)

    def fill(self, selector, value):
        self._gate(f"fill {selector}")
        self.page.fill(selector, value)
