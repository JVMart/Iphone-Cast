"""Usage:
  python -m agent_harness.cli login <url>
  python -m agent_harness.cli read <url> [--selector CSS]
  python -m agent_harness.cli shot <url> <out.png>
  python -m agent_harness.cli click <url> <selector> --allow-write
"""
import argparse

from .harness import Session, allowed_domains


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["login", "read", "shot", "click"])
    p.add_argument("url")
    p.add_argument("arg", nargs="?")
    p.add_argument("--selector", default="body")
    p.add_argument("--allow-write", action="store_true")
    a = p.parse_args()

    if a.cmd == "login":
        s = Session(headless=False)
        s.page.goto(a.url)
        input("Sign in (incl. MFA) in the browser, then press Enter here...")
        s.close()
        return

    s = Session(headless=True, allow_write=a.allow_write)
    try:
        s.goto(a.url)
        if a.cmd == "read":
            print(s.read_text(a.selector))
        elif a.cmd == "shot":
            s.screenshot(a.arg)
        elif a.cmd == "click":
            s.click(a.arg)
    finally:
        s.close()


if __name__ == "__main__":
    if not allowed_domains():
        print("Add domains to agent_harness/allowed_domains.txt first.")
    else:
        main()
