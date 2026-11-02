# Agent browser-session harness

Lets an agent read (and, with approval, act in) web apps using a session **you** signed into.

Setup:
    pip install playwright; python -m playwright install chromium
    # add your work domains to allowed_domains.txt (include the login domain)
    python -m agent_harness.cli login https://outlook.office.com
    python -m agent_harness.cli read https://outlook.office.com/mail --selector "[role=main]"

Safety:
- Passwords/MFA are entered only by you; the profile lives in %LOCALAPPDATA%\agent_harness (outside the repo).
- Domain allowlist; read-only unless `--allow-write`, and each write needs a y/N confirm.
- Every action is logged to `audit.jsonl`.
- Only works within your own permissions. Check your employer's policy on automating work accounts first.
