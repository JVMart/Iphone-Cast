"""Model backends. Keys come from environment variables only (never stored on disk).

  ollama : local model, nothing leaves this PC.
           HARNESS_OLLAMA_MODEL (default llama3.1)
  openai : any OpenAI-compatible chat endpoint you are approved to use.
           HARNESS_LLM_URL (e.g. https://host/v1), HARNESS_LLM_KEY, HARNESS_LLM_MODEL
  none   : no AI; agents fall back to keyword-based extraction.
"""
import json
import os
import urllib.request
from urllib.parse import urlparse

OLLAMA = "http://127.0.0.1:11434"


class LLMError(Exception):
    pass


PREFERRED = ["llama3.1:8b", "ministral-3:8b", "qwen3.5:9b", "gemma4:e4b", "hermes3:8b", "phi4:14b"]


def ollama_models():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=1) as r:
            return [m["name"] for m in json.load(r)["models"]]
    except Exception:
        return []


def ollama_model():
    """HARNESS_OLLAMA_MODEL if set, else a preferred installed model, else the first one."""
    if os.environ.get("HARNESS_OLLAMA_MODEL"):
        return os.environ["HARNESS_OLLAMA_MODEL"]
    have = ollama_models()
    for m in PREFERRED:
        if m in have:
            return m
    return have[0] if have else "llama3.1"


def ollama_up():
    return bool(ollama_models())


def openai_configured():
    return all(os.environ.get(k) for k in ("HARNESS_LLM_URL", "HARNESS_LLM_KEY", "HARNESS_LLM_MODEL"))


def status():
    return {"ollama": ollama_up(), "openai": openai_configured()}


def resolve(choice):
    if choice in ("ollama", "openai", "none"):
        return choice
    return "ollama" if ollama_up() else "none"


def _post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except Exception as e:
        raise LLMError(f"Model call failed: {e}") from e


def complete(system, user, backend):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if backend == "ollama":
        model = ollama_model()
        data = _post(OLLAMA + "/api/chat", {"model": model, "stream": False, "messages": messages,
                                            "options": {"num_ctx": 16384}}, {})
        return data["message"]["content"]
    if backend == "openai":
        if not openai_configured():
            raise LLMError("Set HARNESS_LLM_URL, HARNESS_LLM_KEY and HARNESS_LLM_MODEL first.")
        base = os.environ["HARNESS_LLM_URL"].rstrip("/")
        u = urlparse(base)
        if u.scheme != "https" and u.hostname not in ("127.0.0.1", "localhost"):
            raise LLMError("HARNESS_LLM_URL must be https (or localhost).")
        data = _post(base + "/chat/completions",
                     {"model": os.environ["HARNESS_LLM_MODEL"], "messages": messages},
                     {"Authorization": "Bearer " + os.environ["HARNESS_LLM_KEY"]})
        return data["choices"][0]["message"]["content"]
    raise LLMError("No model backend selected.")
