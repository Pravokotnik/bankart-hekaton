"""Izbere bralnik računov: RECEIPT_READER=local (privzeto) ali claude."""

from __future__ import annotations

import os

from reader.errors import ReceiptError

READER = os.environ.get("RECEIPT_READER", "local")

__all__ = ["READER", "ReceiptError", "is_ready", "parse_receipt"]


def parse_receipt(data: bytes) -> dict:
    """Slika → { items: [{name, quantity, price}], total } (shema iz plan.md 3.1)."""
    if READER == "claude":
        from reader import claude

        return claude.read(data)
    from reader import local

    return local.read(data)


def is_ready() -> bool:
    if READER == "claude":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    from reader import local_llm

    return local_llm.is_ready()
