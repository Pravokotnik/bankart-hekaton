"""Logika deljenja računa. Vsi zneski so v centih (int), nikoli float."""

from __future__ import annotations


def to_cents(amount: float) -> int:
    return int(round(amount * 100))


def split_amount(total: int, weights: list[int], prefer: int | None = None) -> list[int]:
    """Razdeli `total` centov sorazmerno z `weights` (metoda največjega ostanka).

    Vsota rezultata je vedno točno `total`. Odvečne cente dobijo deli z največjim
    ostankom; pri enakem ostanku ima prednost indeks `prefer` (plačnik), nato vrstni red.
    """
    if not weights or sum(weights) <= 0:
        raise ValueError("weights must be positive")
    weight_sum = sum(weights)
    base = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    left = total - sum(base)
    order = sorted(
        range(len(weights)),
        key=lambda i: (-remainders[i], 0 if i == prefer else 1, i),
    )
    for i in order[:left]:
        base[i] += 1
    return base


def expand_items(items: list[dict]) -> list[dict]:
    """Vrstico s `quantity > 1` razbije na posamezne kose s skupnim `group_id`.

    Vhod: [{"name", "quantity", "price"}], kjer je `price` cena celotne vrstice v EUR.
    Izhod: [{"id", "group_id", "name", "price_cents"}], en zapis na kos.
    """
    pieces = []
    for line_no, item in enumerate(items):
        quantity = item.get("quantity") or 1
        quantity = quantity if isinstance(quantity, int) and quantity > 1 else 1
        group_id = f"g{line_no}"
        prices = split_amount(to_cents(item["price"]), [1] * quantity, prefer=0)
        for piece_no, price in enumerate(prices):
            pieces.append({
                "id": f"{group_id}-{piece_no}",
                "group_id": group_id,
                "name": item["name"],
                "price_cents": price,
            })
    return pieces


def compute_breakdown(
    items: list[dict],
    participants: list[str],
    assignments: dict[str, dict[str, int]],
    payer: str,
) -> dict[str, list[dict]]:
    """Za vsakega udeleženca vrne seznam njegovih delov postavk.

    `items`: [{"id", "price_cents", ...}]
    `assignments`: item_id -> {participant_id: delež}
    Vrne participant_id -> [{"item_id", "cents", "of"}], kjer je `of` število
    oseb, ki si postavko delijo.
    """
    breakdown = {p: [] for p in participants}
    for item in items:
        shares = {p: s for p, s in assignments.get(item["id"], {}).items() if s > 0}
        if not shares:
            raise ValueError(f"item {item['id']} is not assigned")
        unknown = set(shares) - set(breakdown)
        if unknown:
            raise ValueError(f"unknown participants: {sorted(unknown)}")
        people = [p for p in participants if p in shares]
        prefer = people.index(payer) if payer in people else None
        parts = split_amount(item["price_cents"], [shares[p] for p in people], prefer)
        for person, part in zip(people, parts):
            breakdown[person].append({"item_id": item["id"], "cents": part, "of": len(people)})
    return breakdown


def compute_shares(
    items: list[dict],
    participants: list[str],
    assignments: dict[str, dict[str, int]],
    payer: str,
) -> dict[str, int]:
    """Izračuna, koliko centov dolguje vsak udeleženec (vključno s plačnikom).

    Vsota je enaka vsoti postavk.
    """
    breakdown = compute_breakdown(items, participants, assignments, payer)
    return {p: sum(part["cents"] for part in parts) for p, parts in breakdown.items()}
