"""Iz OCR škatel sestavi vrstice računa, kot jih vidi človek."""

from __future__ import annotations

import re

from .ocr import Box

MIN_SCORE = 0.6
# OCR okrasne zvezdice in črte pogosto prebere kot kitajske znake.
_JUNK = re.compile(r"[　-鿿]")


def build_lines(boxes: list[Box]) -> list[str]:
    """Škatle z isto višino združi v vrstico, jih uredi od leve proti desni
    in stolpce loči z " | ". Izpusti nezanesljive in okrasne škatle."""
    useful = [b for b in boxes if b.score >= MIN_SCORE and not _JUNK.search(b.text) and b.text.strip()]
    rows: list[list[Box]] = []
    for box in sorted(useful, key=lambda b: b.y_mid):
        row = rows[-1] if rows else None
        # Ista vrstica, če je sredina škatle dovolj blizu sredine vrstice.
        if row and abs(box.y_mid - row[0].y_mid) <= max(box.height, row[0].height) * 0.6:
            row.append(box)
        else:
            rows.append([box])
    return [" | ".join(b.text.strip() for b in sorted(row, key=lambda b: b.x0)) for row in rows]
