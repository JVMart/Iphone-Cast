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

Local UI: `python -m agent_harness.ui` (opens http://127.0.0.1:8765).

Agents (read-only, work only on the local index in `%LOCALAPPDATA%\agent_harness\index.db`):
- Index: web reads, uploaded files (.eml/.txt/.md/.html/.csv) and pasted text, searchable and tagged.
- Summarize, Flag important, Compare & questions (finds same/similar documents), and Ask (searches the index).
- Results are remembered as cards for later reference.

Models (pick in the UI):
- Local Ollama (nothing leaves your PC; `HARNESS_OLLAMA_MODEL`, default llama3.1).
- Your API: set `HARNESS_LLM_URL` (https, OpenAI-compatible `/chat/completions`), `HARNESS_LLM_KEY`, `HARNESS_LLM_MODEL`. Keys are read from env only. The UI requires a permission checkbox before sending documents.
- No AI: keyword-based fallback.

The index holds work email text; protect it and follow your employer's data policy.

