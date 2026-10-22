"""Lokalni bralnik: OCR (ONNX Runtime) → vrstice → tabela / pravila, po potrebi Qwen3-4B.

1. Tabela ("lažni CSV"): številke pripišemo stolpcem iz glave po položaju in pokvarjene
   zneske izračunamo iz količina × cena − popust; zneske izberemo tako, da se ujema vsota.
2. Pravila: za račune brez tabele (lokali, dvovrstične postavke "2x4,50").
3. Model: le če se vsota še vedno ne ujema in ima račun < 10 postavk."""

from __future__ import annotations

import time

from . import local_llm
from .errors import ReceiptError
from .lines import build_rows, row_text
from .ocr import Box, read_boxes
from .postprocess import _TOTAL_LINE, find_total, gap, parse_by_rules, resolve_item_lines, sum_matches, trim_to_total
from .repair import choose
from .table import parse_table

# Pri dolgih računih je razlika skoraj vedno ena napačno prebrana številka, ki je model ne
# more popraviti (zneske jemljemo iz besedila). Model bi tam porabil 12–22 s brez koristi.
SKIP_MODEL_FROM_ITEMS = 10


def parse_rows(rows: list[list[Box]]) -> tuple[dict, list[str]]:
    """Brez modela: vrne najboljši rezultat (tabela ali pravila) in vrstice za model."""
    lines = trim_to_total([row_text(r) for r in rows])
    rows = rows[: len(lines)]
    total = find_total(lines) or 0.0

    candidates = [parse_by_rules(lines)]
    table = parse_table(rows, lines, _TOTAL_LINE)
    if table:
        candidates.insert(0, {"items": choose(table, int(round(total * 100))), "total": total, "method": "table"})
    for candidate in candidates:
        if sum_matches(candidate):
            return candidate, lines
    return min(candidates, key=gap), lines


def read(data: bytes) -> dict:
    timings = {}
    start = time.perf_counter()
    rows = build_rows(read_boxes(data))
    timings["ocr_ms"] = int((time.perf_counter() - start) * 1000)
    if not rows:
        raise ReceiptError("Na sliki ni mogoče prebrati besedila. Slikaj račun bliže in bolj osvetljen.")

    receipt, lines = parse_rows(rows)
    timings["method"] = receipt.pop("method", "rules")
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
