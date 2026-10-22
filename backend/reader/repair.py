"""Izbere zneske vrstic tako, da se vsota ujema s končnim zneskom računa.

Vsaka vrstica ima eno ali več možnosti (prebran znesek, izračunan iz količina × cena − popust).
Če kombinacija možnosti da točno "Skupaj", jo vzamemo. Če en sam znesek manjka povsem,
ga izračunamo kot razliko do "Skupaj"."""

from __future__ import annotations

from itertools import product

from .table import Row

MAX_COMBINATIONS = 4096


def choose(rows: list[Row], total_cents: int | None) -> list[dict]:
    known = [r for r in rows if r.options]
    unknown = [r for r in rows if not r.options]
    picks = {id(r): r.options[0] for r in known}

    if total_cents:
        ambiguous = [r for r in known if len(r.options) > 1]
        fixed = sum(picks[id(r)][0] for r in known if len(r.options) == 1)
        combos = 1
        for r in ambiguous:
            combos *= len(r.options)
        matched = False
        if not unknown and combos <= MAX_COMBINATIONS:
            for choice in product(*(r.options for r in ambiguous)):
                if fixed + sum(c[0] for c in choice) == total_cents:
                    picks.update({id(r): c for r, c in zip(ambiguous, choice)})
                    matched = True
                    break
        if not matched and len(unknown) == 1:
            remainder = total_cents - sum(picks[id(r)][0] for r in known)
            if 0 < remainder < total_cents:
                picks[id(unknown[0])] = (remainder, 1)

    items = []
    for r in rows:
        if id(r) in picks:
            price, quantity = picks[id(r)]
            items.append({"name": r.name, "quantity": quantity, "price": price / 100})
    return items
