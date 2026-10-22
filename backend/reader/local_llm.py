"""Klic lokalnega modela (Qwen3-4B-Instruct-2507 v llama-server) z vsiljeno JSON shemo.

Model ne prepisuje imen in cen, ampak vrne samo številke vrstic z izdelki, npr. [8, 9, 12].
Tako napiše ~2 žetona na postavko namesto ~30 (na tem prenosniku piše ~15 žetonov/s, zato
je dolžina odgovora glavni vir časa) in ne more izmisliti zneska."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import ReceiptError

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8081")
TIMEOUT_S = 120

PROMPT = """Spodaj je besedilo računa, prebrano z OCR. Vsaka vrstica ima na začetku številko, stolpci so ločeni z " | ".

Vrni JSON:
- lines: številke vrstic, v katerih je IME kupljenega izdelka (samo številke, npr. [8, 9, 12]).
- total: končni znesek za plačilo (Skupaj, Za plačilo, Znesek) kot število.

Ne vključi glave, vmesnih vsot, DDV, načina plačila, gotovine, vračila in darilnih kartic.
Če je izdelek v dveh vrsticah (ime, nato količina in cena), vrni samo vrstico z imenom.

Račun:
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {"type": "array", "items": {"type": "integer"}},
        "total": {"type": "number"},
    },
    "required": ["lines", "total"],
}


def is_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{LLM_URL}/health", timeout=1) as res:
            return res.status == 200
    except (urllib.error.URLError, OSError):
        return False


def number_lines(lines: list[str]) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(lines, start=1))


def extract(numbered_text: str, previous: dict | None = None, feedback: str | None = None) -> dict:
    """Vrne {"lines": [številke vrstic z izdelki], "total": float}."""
    messages = [{"role": "user", "content": PROMPT + numbered_text}]
    if previous is not None and feedback:
        messages += [
            {"role": "assistant", "content": json.dumps(previous, separators=(",", ":"))},
            {"role": "user", "content": feedback},
        ]
    body = {
        "messages": messages,
        "temperature": 0,
        "cache_prompt": True,
        "response_format": {"type": "json_schema", "json_schema": {"schema": SCHEMA}},
    }
    request = urllib.request.Request(
        f"{LLM_URL}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as res:
            out = json.load(res)
    except urllib.error.HTTPError as e:
        raise ReceiptError(f"Lokalni model je vrnil napako ({e.code}).") from e
    except TimeoutError as e:
        raise ReceiptError("Lokalni model se ni odzval pravočasno. Poskusi znova ali vnesi ročno.") from e
    except (urllib.error.URLError, OSError) as e:
        raise ReceiptError("Lokalni model ne teče. Zaženi llama-server (glej README).") from e
    try:
        return json.loads(out["choices"][0]["message"]["content"])
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ReceiptError("Lokalni model ni vrnil veljavnega rezultata.") from e
