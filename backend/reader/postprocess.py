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
    r"^\s*(skupa\W?[ji]\w*|za pla[čc]ilo|še za pla[čc]ilo|znesek|vmesna vsota|me[đdu]+zbroj|ukupno|total|summe|"
    r"ddv|gotovina|vra[čc]ilo|kartica|darilna kartica|pla[čc]ilo|popust na račun|eur|izdelek|artikel|"
    r"visa|maestro|mastercard|\+?\s*tip|satz|netto|neto|bruto|osnova|stopnja|mwst)\b",
    re.IGNORECASE,
)
_TOTAL_LINE = re.compile(r"^\s*(skupa\W?[ji]|za pla[čc]ilo|znesek|ukupno|total|summe)", re.IGNORECASE)
_HEADER_LINE = re.compile(r"(izdelek|artikel|opis|naziv).*(znesek|vrednost|cena)", re.IGNORECASE)
# Znesek z dvema decimalkama, tudi s tisočicami: "8,50", "6.84", "3.758,75".
_AMOUNT = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:\.\d{3})+,\d{2}|\d+[.,]\d{2})(?![\d%])(?!\s*%)")
# Količina v stolpcu: celo število ali decimalka ("1", "2,00", "0.796").
_QTY_TOKEN = re.compile(r"\d{1,3}(?:[.,]\d{1,3})?")
# Količina z enoto: "4,00 | KOS", "1.00 kom".
_QTY_WITH_UNIT = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,]0{1,3})?)\s*(?:\|\s*)?(?:kos|kom|kpl)\b", re.IGNORECASE)
_QTY_HEADER = re.compile(r"^\W*ko[l1i]", re.IGNORECASE)
# Datum ali ura v vrstici (glava računa): "21.10.26", "18:24:27".
_DATE_OR_TIME = re.compile(r"\b\d{1,2}[.:/]\d{1,2}[.:/]\d{2,4}\b|\b\d{1,2}:\d{2}\b")
_UNIT_WORD = re.compile(r"^(kos|kom|kpl|kg|g|l|eur|em|me)\.?$", re.IGNORECASE)
# Številka, ki jo je OCR pokvaril ("66.0" namesto "0,99"), ali manjkajoča decimalka.
_BROKEN_NUMBER = re.compile(r"(?<![\d.,])\d+[.,]\d(?![\d])|[^\w\s|.,]\d{2}\b")
# "2x4,50", "2 x 4,50" ali samostojen "2x"; ne "Kam.2x50k" ali "15x10kos" v imenu.
_QTY_MARKER = re.compile(r"(?<![\w.,])(\d{1,2})(?:[.,]0{1,3})?\s*[xX×*](?:\s*(\d+[.,]\d{2}))?(?!\w)")
# Znesek z minusom na koncu vrstice: popust ali storno.
_NEGATIVE = re.compile(r"-\s*(\d+[.,]\d{2})\s*(?:\|\s*[A-Ea-e])?\s*$")
# Vrstica s ceno na kg nad imenom izdelka (Eurospin: "Net 2,092kg x 0,95 EUR/kg").
_PER_KG = re.compile(r"/\s*kg", re.IGNORECASE)
MAX_QUANTITY = 50


def to_cents(text: str) -> int:
    if "." in text and "," in text:  # tisočice: 3.758,75
        text = text.replace(".", "")
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
        letters_only = re.sub(r"[\d.,\s]+", " ", part).strip()
        if len(re.findall(r"[^\W\d_]", part)) >= 2 and not _UNIT_WORD.match(letters_only):
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


def quantity_column(lines: list[str]) -> int | None:
    """Indeks stolpca "Količina"/"Kol." v glavi tabele (OCR ga zapiše tudi kot "Kolidina")."""
    for line in lines:
        if _HEADER_LINE.search(line) or re.match(r"^\W*ko[l1i]", line, re.IGNORECASE):
            for i, part in enumerate(line.split(" | ")):
                if _QTY_HEADER.search(part):
                    return i
    return None


def _consistent(quantity: int, price: int, others: list[int]) -> bool:
    """Ali se količina ujema z zneski v vrstici: količina × cena kosa = znesek,
    ali količina × cena kosa − popust = znesek (Spar: "2 | 1,79 | 0,50 | 3,08")."""
    for unit in others:
        if abs(quantity * unit - price) <= 1:
            return True
        if any(abs(quantity * unit - discount - price) <= 1 for discount in others if discount != unit):
            return True
    return False


def find_quantity(item_lines: list[str], price: int, qty_col: int | None) -> int:
    """Celo število kosov. Decimalne količine (teža, npr. 0,796 kg) so 1 kos.

    Vrstni red dokazov:
    1. oznaka "2x" ali "2x4,50",
    2. količina z enoto: "4,00 | KOS", "1.00 kom",
    3. stolpec "Količina" iz glave tabele ("1", "2", "1,00"),
    4. celo število kjerkoli v vrstici,
    5. izračun iz zneskov: "14.00 | 28.00" → 2.
    Količina ≥ 2 iz 3.–4. mora ustrezati zneskom (cena kosa × količina), da oznaka DDV "2"
    ali "30kos" v imenu ne štejeta."""
    # Števila v imenu izdelka ("ÜLTJE 4", "30kos") niso količina, zato ime odrežemo.
    rest_lines = []
    for line in item_lines:
        name = item_name(line)
        rest_lines.append(line.replace(name, " ", 1) if name else line)
    text = "\n".join(item_lines)
    rest = "\n".join(rest_lines)

    marker = _QTY_MARKER.search(text)
    if marker and 1 <= int(marker.group(1)) <= MAX_QUANTITY:
        return int(marker.group(1))

    with_unit = _QTY_WITH_UNIT.search(rest)
    if with_unit:
        value = float(with_unit.group(1).replace(",", "."))
        if value.is_integer() and 1 <= value <= MAX_QUANTITY:
            return int(value)

    def others(span: tuple[int, int] | None = None, source: str = rest) -> list[int]:
        without = source[: span[0]] + " " + source[span[1]:] if span else source
        return [a for a in amounts(without) if a != price]

    if qty_col is not None:
        for line in item_lines:
            parts = line.split(" | ")
            if qty_col < len(parts) and _QTY_TOKEN.fullmatch(parts[qty_col].strip()):
                token = parts[qty_col].strip()
                value = float(token.replace(",", "."))
                if re.search(r"[.,]\d{3}$", token) and not value.is_integer():
                    return 1  # teža (0,796 kg): ni kosov
                if not value.is_integer():
                    break  # 2 decimalki: OCR je količino izpustil, v stolpcu je cena kosa
                position = line.find(token)
                rest_of_line = others((position, position + len(token)), line)
                digits = token.split(",")[0].split(".")[0]
                if not token.isdigit():
                    # "1,00", "2,00": količina z decimalkami; obdržimo jo le, če se ujema z zneski.
                    q = int(value)
                    if q == 1 or (2 <= q <= MAX_QUANTITY and _consistent(q, price, rest_of_line)):
                        return q
                    break
                # OCR včasih količini doda števko ("21" namesto "2"), zato poskusimo tudi začetek.
                for k in range(len(digits), 0, -1):
                    q = int(digits[:k])
                    if q == 1:
                        return 1
                    if 2 <= q <= MAX_QUANTITY and _consistent(q, price, rest_of_line):
                        return q
                # Cene kosa ni mogoče prebrati: zaupamo stolpcu "Količina".
                q = int(digits[0]) if len(digits) > 1 else int(digits)
                if 2 <= q <= 9 and (_BROKEN_NUMBER.search(line) or not [a for a in rest_of_line if a]):
                    return q
                break

    for match in re.finditer(r"(?<![\w.,])(\d{1,2})(?:[.,]0{1,3})?(?![\w.,\d])", rest):
        q = int(match.group(1))
        if 2 <= q <= MAX_QUANTITY and _consistent(q, price, others(match.span())):
            return q

    all_amounts = amounts(rest)
    found = [a for a in all_amounts if a != price]
    if len(all_amounts) >= 3:
        # Pri treh zneskih (cena kosa | popust | znesek) je izračun mogoč le iz cene kosa,
        # ki je prvi znesek; cela "1,00" ali "2,00" je tam najverjetneje količina.
        found = [a for a in found[:1] if not (a % 100 == 0 and a <= MAX_QUANTITY * 100)]
    for unit in found:
        if unit > 0 and price % unit == 0 and 2 <= price // unit <= 20:
            return price // unit
    return 1


def _item(name: str, price_text: str, item_lines: list[str], qty_col: int | None) -> dict | None:
    price, _ = line_amount(price_text)
    if not price or price <= 0:
        return None
    return {"name": name, "quantity": find_quantity(item_lines, price, qty_col), "price": price / 100}


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
    qty_col = quantity_column(lines[:start] if start else lines)
    items, pending = [], None
    orphans, last_cut = [], None
    for line in lines[start:end]:
        name = item_name(line)
        if _PER_KG.search(line) or _DATE_OR_TIME.search(line):
            continue
        negative = _NEGATIVE.search(line)
        if negative and items:
            # Popust ali storno z minusom ("VRSTIČNI POPUST EUR | -9,98") zmanjša prejšnjo postavko.
            cut = to_cents(negative.group(1)) / 100
            if cut == last_cut:
                continue  # OCR je isti popust prebral v dveh vrsticah ("-9.98" in "POPUST | -9,98")
            last_cut = cut
            if cut < items[-1]["price"]:
                items[-1]["price"] = round(items[-1]["price"] - cut, 2)
            elif abs(cut - items[-1]["price"]) < 0.005:
                items.pop()
            pending = None
            continue
        if name and _NOT_ITEM.search(name):
            pending = None
            continue
        if name and amounts(line):
            item = _item(name, line, [line], qty_col)
            if item:
                items.append(item)
            pending = None
        elif name:
            pending = name
        elif pending and (amounts(line) or _QTY_MARKER.search(line)):
            item = _item(pending, line, [line], qty_col)
            if item:
                items.append(item)
            pending = None
        elif items and len(amounts(line)) == 1 and not item_name(line):
            orphans.append(amounts(line)[0])
    total = find_total(lines) or 0.0
    # Znesek brez imena (OCR imena ni prebral): dodamo ga le, če z njim vsota točno ustreza.
    missing = int(round(total * 100)) - sum(int(round(i["price"] * 100)) for i in items)
    if missing > 0 and missing in orphans:
        items.append({"name": "Izdelek (ime ni prebrano)", "quantity": 1, "price": missing / 100})
    return {"items": items, "total": total}


def resolve_item_lines(numbers: list[int], lines: list[str], total: float) -> dict:
    """Model pove samo številke vrstic z imeni izdelkov (od 1). Znesek je v isti vrstici
    ali v naslednji, če ta nima imena (npr. "C HEINIKEN 0%" / "3,20 | 2x | 6,40")."""
    qty_col = quantity_column(lines)
    items, seen = [], set()
    for no in numbers:
        if not 1 <= no <= len(lines) or no in seen:
            continue
        seen.add(no)
        line = lines[no - 1]
        name = item_name(line)
        if not name or _NOT_ITEM.search(name) or _DATE_OR_TIME.search(line):
            continue
        following = lines[no] if no < len(lines) else ""
        if amounts(line):
            item = _item(name, line, [line], qty_col)
        elif not item_name(following):
            item = _item(name, following, [line, following], qty_col)
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
