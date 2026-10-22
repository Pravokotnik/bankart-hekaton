"""Lokalni bralnik: OCR (ONNX Runtime) → vrstice → pravila, po potrebi Qwen3-4B-Instruct-2507.

Najprej poskusimo s pravili (brez modela, ~0 s). Model pokličemo le, če se vsota postavk
ne ujema s končnim zneskom. Tako je večina računov prebrana v času OCR (2–5 s)."""

from __future__ import annotations

import time

from . import local_llm
from .errors import ReceiptError
from .lines import build_lines
from .ocr import read_boxes
from .postprocess import gap, parse_by_rules, resolve_item_lines, sum_matches, trim_to_total

# Pri dolgih računih (tabela z ≥ 10 postavkami) so pravila skoraj vedno pravilna, razlika pa
# izvira iz ene napačno prebrane številke, ki je model ne more popraviti (zneske jemljemo iz
# besedila). Model bi tam porabil 12–22 s brez koristi, zato ga preskočimo.
SKIP_MODEL_FROM_ITEMS = 10


def read(data: bytes) -> dict:
    timings = {}
    start = time.perf_counter()
    lines = trim_to_total(build_lines(read_boxes(data)))
    timings["ocr_ms"] = int((time.perf_counter() - start) * 1000)
    if not lines:
        raise ReceiptError("Na sliki ni mogoče prebrati besedila. Slikaj račun bliže in bolj osvetljen.")

    receipt = parse_by_rules(lines)
    timings["method"] = "rules"
    if not sum_matches(receipt) and len(receipt["items"]) < SKIP_MODEL_FROM_ITEMS:
        start = time.perf_counter()
        raw = local_llm.extract(local_llm.number_lines(lines))
        by_model = resolve_item_lines(raw.get("lines", []), lines, raw.get("total", 0))
        timings["llm_ms"] = int((time.perf_counter() - start) * 1000)
        # Obdržimo rezultat, ki je bližje končnemu znesku; razliko uporabnik vidi v UI.
        if gap(by_model) < gap(receipt):
            receipt = by_model
            timings["method"] = "model"

    if not receipt["items"]:
        raise ReceiptError("Na računu ni bilo mogoče najti postavk. Poskusi znova ali jih vnesi ročno.")
    return {**receipt, "timings": timings}
