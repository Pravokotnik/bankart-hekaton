"""Račun s tabelo (Izdelek | Količina | Cena | Popust | Znesek) prebere kot CSV.

Vsako besedo pripiše stolpcu iz glave tabele po položaju x, ne po vrstnem redu. Tako vemo,
katera številka je količina, cena kosa, popust in znesek, in lahko pokvarjen ali manjkajoč
znesek izračunamo: znesek = količina × cena − popust. Vsaka vrstica dobi eno ali več
možnosti (prebran znesek, izračunan znesek); katera je prava, izbere `repair` po vsoti."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ocr import Box

ROLES = [
    ("name", re.compile(r"izdelek|artikel|naziv|opis", re.IGNORECASE)),
    ("qty", re.compile(r"^\W*ko[l1i]", re.IGNORECASE)),
    ("unit", re.compile(r"^\W*(cena|cijena)", re.IGNORECASE)),
    ("discount", re.compile(r"popust|rabat", re.IGNORECASE)),
    ("total", re.compile(r"znesek|vrednost|vrednoet|iznos", re.IGNORECASE)),
]
NUMERIC_ROLES = ("qty", "unit", "discount", "total")
MAX_QUANTITY = 50

_AMOUNT = re.compile(r"^-?(?:\d{1,3}(?:\.\d{3})+,\d{2}|\d+[.,]\d{2})$")
_QTY = re.compile(r"^-?\d{1,4}(?:[.,]\d{1,3})?$")
_VAT_CODE = re.compile(r"^[A-Ea-e]$")


@dataclass
class Word:
    text: str
    x: float  # sredina besede


@dataclass
class Row:
    name: str
    options: list[tuple[int, int]] = field(default_factory=list)  # (znesek v centih, količina)
    storno: bool = False
    source: str = ""


def words(row: list[Box]) -> list[Word]:
    """Škatle razbije na besede in vsaki oceni položaj x po mestu v škatli."""
    out = []
    for box in row:
        text = box.text.strip()
        if not text:
            continue
        for m in re.finditer(r"\S+", text):
            center = (m.start() + m.end()) / 2 / len(text)
            out.append(Word(m.group(), box.x0 + center * (box.x1 - box.x0)))
    return out


def header_columns(row: list[Box]) -> dict[str, float] | None:
    """{vloga: x} iz glave tabele. Vrne None, če glava nima vsaj dveh številskih stolpcev."""
    columns: dict[str, float] = {}
    for word in words(row):
        for role, pattern in ROLES:
            if role not in columns and pattern.search(word.text):
                columns[role] = word.x
                break
    if sum(role in columns for role in NUMERIC_ROLES) < 2 or "total" not in columns:
        return None
    return columns


def to_cents(text: str) -> int:
    negative = text.startswith("-")
    text = text.lstrip("-")
    if "." in text and "," in text:
        text = text.replace(".", "")
    cents = int(round(float(text.replace(",", ".")) * 100))
    return -cents if negative else cents


def _quantity_candidates(token: str | None) -> tuple[list[int], float | None]:
    """Možne cele količine in teža (decimalna količina) iz celice "Količina"."""
    if token is None:
        return [1], None
    token = token.lstrip("-")
    if not _QTY.match(token):
        return [1], None
    if re.search(r"[.,]", token):
        value = float(token.replace(",", "."))
        if value.is_integer():
            return [int(value)], None
        return [1], value  # teža: 1 kos
    # OCR doda števke ("21", "221", "1221" namesto "2"), zato poskusimo tudi začetke.
    return [int(token[:k]) for k in range(len(token), 0, -1) if 1 <= int(token[:k]) <= MAX_QUANTITY], None


def parse_row(row: list[Box], columns: dict[str, float]) -> Row | None:
    numeric = {role: x for role, x in columns.items() if role in NUMERIC_ROLES}
    first_numeric_x = min(numeric.values())
    name_words, cells = [], {}
    for word in words(row):
        is_number = bool(_QTY.match(word.text) or _AMOUNT.match(word.text))
        # Besede levo od prvega številskega stolpca so ime (tudi "SEMENA 2" v imenu).
        if word.x < first_numeric_x - 15 and not (is_number and name_words and word.x > first_numeric_x - 40):
            name_words.append(word.text)
            continue
        if _VAT_CODE.match(word.text):
            continue
        role = min(numeric, key=lambda r: abs(numeric[r] - word.x))
        cells.setdefault(role, word.text)
    name = " ".join(name_words).strip()
    if len(re.findall(r"[^\W\d_]", name)) < 2:
        return None

    total_text = cells.get("total")
    total = to_cents(total_text) if total_text and _AMOUNT.match(total_text) else None
    unit = to_cents(cells["unit"]) if "unit" in cells and _AMOUNT.match(cells["unit"]) else None
    discount = to_cents(cells["discount"]) if "discount" in cells and _AMOUNT.match(cells["discount"]) else 0
    quantities, weight = _quantity_candidates(cells.get("qty"))
    storno = (total is not None and total < 0) or str(cells.get("qty", "")).startswith("-")

    computed = []
    if unit is not None:
        if weight is not None:
            computed.append((int(round(weight * unit)) - abs(discount), 1))
        else:
            computed += [(q * unit - abs(discount), q) for q in quantities[:3]]
    computed = [(price, q) for price, q in computed if price > 0]

    options: list[tuple[int, int]] = []
    if total is not None:
        total = abs(total)
        match = next(((p, q) for p, q in computed if abs(p - total) <= 1), None)
        if match:
            options = [(total, match[1])]
        else:
            # Količino iz razmerja zneskov, če je ni v stolpcu ("SPAR JAJCA | 3,09 | 0,00 | 6,18").
            q = total // unit if unit and total % unit == 0 and 2 <= total // unit <= 20 else (
                quantities[0] if weight is None and unit and quantities[0] * unit == total else 1)
            options = [(total, q)] + [c for c in computed if c[0] != total]
    else:
        options = computed
    return Row(name=name, options=options, storno=storno, source=" | ".join(w.text for w in words(row)))


def parse_table(rows: list[list[Box]], lines: list[str], total_line: re.Pattern) -> list[Row] | None:
    """Vrstice tabele med glavo in vrstico s končnim zneskom. None, če glave ni."""
    for i, row in enumerate(rows):
        columns = header_columns(row)
        if columns:
            break
    else:
        return None
    out: list[Row] = []
    for row, line in zip(rows[i + 1:], lines[i + 1:]):
        if total_line.search(line):
            break
        parsed = parse_row(row, columns)
        if not parsed:
            continue
        if parsed.storno:
            # Storno: odstrani enak izdelek, sicer je to popust prejšnje vrstice.
            same = next((r for r in reversed(out) if r.name == parsed.name), None)
            if same:
                out.remove(same)
            continue
        out.append(parsed)
    return out
