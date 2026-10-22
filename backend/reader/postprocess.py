"""Iz OCR vrstic sestavi postavke. Imena in zneske vedno vzame neposredno iz besedila,
zato jih model ne more izmisliti.

Dva načina:
- `parse_by_rules`: brez modela, za račune z običajno postavitvijo (ime | … | znesek).
- `resolve_item_lines`: model pove samo, katere vrstice so izdelki; ostalo naredi koda.
"""

from __future__ import annotations

import re

# Vrstice, ki so vsote, plačila ali glava, ne izdelki.
_NOT_ITEM = re.compile(
    r"^\s*(skupaj|skupa\W?j|za plačilo|še za plačilo|znesek|vmesna vsota|međuzbroj|ukupno|total|"
    r"ddv|gotovina|vračilo|kartica|darilna kartica|plačilo|popust na račun|eur|izdelek|artikel)\b",
    re.IGNORECASE,
)
_TOTAL_LINE = re.compile(r"^\s*(skupaj|skupa\W?j|za plačilo|znesek|ukupno|total)\b", re.IGNORECASE)
_HEADER_LINE = re.compile(r"(izdelek|artikel|opis|naziv).*(znesek|vrednost|cena)", re.IGNORECASE)
_AMOUNT = re.compile(r"(?<![\d.,])\d+[.,]\d{2}(?![\d])")
# "2x4,50", "2 x 4,50" ali samostojen "2x"; ne "Kam.2x50k" ali "15x10kos" v imenu.
_QTY_MARKER = re.compile(r"(?<![\w.,])(\d{1,2})\s*[xX×](?:\s*(\d+[.,]\d{2}))?(?!\w)")
# Vrstica s ceno na kg nad imenom izdelka (Eurospin: "Net 2,092kg x 0,95 EUR/kg").
_PER_KG = re.compile(r"/\s*kg", re.IGNORECASE)
MAX_QUANTITY = 50


def to_cents(text: str) -> int:
    return int(round(float(text.replace(",", ".")) * 100))


def trim_to_total(lines: list[str]) -> list[str]:
    """Odreže vse za vrstico s končnim zneskom (DDV tabela, ZOI/EOR, reklame).
    Obdrži še eno vrstico, ker je znesek včasih pod oznako ("Za plačilo:" / "EUR 32,40")."""
    for i, line in enumerate(lines):
        if _TOTAL_LINE.search(line):
            return lines[: i + 2]
    return lines


def item_name(line: str) -> str | None:
    """Prvi stolpec z vsaj dvema črkama, npr. "KRAČE PIŠČANČJE IK | 0.796 | 2.38 B" → "KRAČE PIŠČANČJE IK"."""
    for part in line.split(" | "):
        part = part.strip()
        if len(re.findall(r"[^\W\d_]", part)) >= 2:
            return part
    return None


def amounts(line: str) -> list[int]:
    return [to_cents(a) for a in _AMOUNT.findall(line)]


def line_amount(line: str) -> tuple[int | None, int | None]:
    """Znesek vrstice (v centih) in količina iz oznake "NxU", če obstaja.

    Znesek je zadnji znesek v vrstici, ki ni del oznake "NxU". Če ga ni (OCR je npr.
    9,00 prebral kot "00'6"), ga izračunamo iz oznake: 2x4,50 → 9,00."""
    marker = _QTY_MARKER.search(line)
    quantity = int(marker.group(1)) if marker else None
    unit = to_cents(marker.group(2)) if marker and marker.group(2) else None
    rest = line[: marker.start()] + line[marker.end():] if unit is not None else line
    found = amounts(rest)
    if found:
        return found[-1], quantity
    if unit is not None and quantity:
        return unit * quantity, quantity
    return None, quantity


def derive_quantity(text: str, price: int, marked: int | None) -> int:
    """Količina ≥ 2 potrebuje dokaz na računu: oznako "2x" ali stolpec s celim številom,
    ki pomnožen s ceno kosa da znesek (Spar: "2 | 1,79 | 0,00 | 3,58"). Oznaka DDV "2"
    ali "30kos" v imenu nista dokaz."""
    if marked and 1 <= marked <= MAX_QUANTITY:
        return marked
    for token in re.findall(r"(?<![\w.,])(\d{1,2})(?![\w.,])", text):
        n = int(token)
        if 2 <= n <= MAX_QUANTITY and any(a * n == price for a in amounts(text) if a != price):
            return n
    return 1


def _item(name: str, price_text: str, all_text: str) -> dict | None:
    price, marked = line_amount(price_text)
    if not price or price <= 0:
        return None
    quantity = derive_quantity(all_text, price, marked)
    return {"name": name, "quantity": quantity, "price": price / 100}


def find_total(lines: list[str]) -> float | None:
    """Znesek v vrstici "Skupaj/Za plačilo", sicer v vrstici pred ali za njo."""
    for i, line in enumerate(lines):
        if _TOTAL_LINE.search(line):
            for j in (i, i - 1, i + 1):
                if 0 <= j < len(lines) and amounts(lines[j]):
                    return amounts(lines[j])[-1] / 100
    return None


def parse_by_rules(lines: list[str]) -> dict:
    """Postavke med glavo tabele ("Izdelek … Znesek") in vrstico "Skupaj", brez modela.
    Ime brez zneska + naslednja vrstica samo s številkami = ena postavka (dvovrstične postavke)."""
    start = next((i + 1 for i, line in enumerate(lines) if _HEADER_LINE.search(line)), 0)
    end = next((i for i, line in enumerate(lines) if i >= start and _TOTAL_LINE.search(line)), len(lines))
    items, pending = [], None
    for line in lines[start:end]:
        name = item_name(line)
        if _PER_KG.search(line):
            continue
        if name and _NOT_ITEM.search(name):
            pending = None
            continue
        if name and amounts(line):
            item = _item(name, line, line)
            if item:
                items.append(item)
            pending = None
        elif name:
            pending = name
        elif pending and (amounts(line) or _QTY_MARKER.search(line)):
            item = _item(pending, line, line)
            if item:
                items.append(item)
            pending = None
    return {"items": items, "total": find_total(lines) or 0.0}


def resolve_item_lines(numbers: list[int], lines: list[str], total: float) -> dict:
    """Model pove samo številke vrstic z imeni izdelkov (od 1). Znesek je v isti vrstici
    ali v naslednji, če ta nima imena (npr. "C HEINIKEN 0%" / "3,20 | 2x | 6,40")."""
    items, seen = [], set()
    for no in numbers:
        if not 1 <= no <= len(lines) or no in seen:
            continue
        seen.add(no)
        line = lines[no - 1]
        name = item_name(line)
        if not name or _NOT_ITEM.search(name):
            continue
        following = lines[no] if no < len(lines) else ""
        if amounts(line):
            item = _item(name, line, line)
        elif not item_name(following):
            item = _item(name, following, f"{line}\n{following}")
        else:
            item = None
        if item:
            items.append(item)
    return {"items": items, "total": find_total(lines) or round(float(total), 2)}


def sum_matches(receipt: dict) -> bool:
    return bool(receipt["items"]) and abs(sum(i["price"] for i in receipt["items"]) - receipt["total"]) < 0.005


def gap(receipt: dict) -> float:
    if not receipt["items"]:
        return float("inf")
    return abs(sum(i["price"] for i in receipt["items"]) - receipt["total"])
