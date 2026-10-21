"""FastAPI strežnik za Flik Razdeli račun (proof of concept, vse v pomnilniku)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from parse_receipt import ReceiptError, parse_receipt
from split import compute_breakdown, expand_items

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
DEMO_RECEIPT = Path(__file__).with_name("demo_receipt.json")

app = FastAPI(title="Flik Razdeli račun")

# Izmišljeni kontakti za demo; "jaz" je vedno plačnik.
CONTACTS = [
    {"id": "jaz", "name": "Jaz", "phone": "+386 40 000 000", "color": "#8ee06a"},
    {"id": "ana", "name": "Ana Novak", "phone": "+386 41 234 567", "color": "#f0a04b"},
    {"id": "miha", "name": "Miha Kovač", "phone": "+386 31 345 678", "color": "#6fb6ff"},
    {"id": "lara", "name": "Lara Horvat", "phone": "+386 40 456 789", "color": "#e57bd0"},
    {"id": "jaka", "name": "Jaka Zupan", "phone": "+386 51 567 890", "color": "#f2d14b"},
    {"id": "tina", "name": "Tina Potočnik", "phone": "+386 70 678 901", "color": "#5fd4c4"},
    {"id": "luka", "name": "Luka Kranjc", "phone": "+386 68 789 012", "color": "#ff8a7a"},
]
CONTACTS_BY_ID = {c["id"]: c for c in CONTACTS}
PAYER = "jaz"

REQUESTS: list[dict] = []


def _receipt_response(parsed: dict, source: str) -> dict:
    items = expand_items(parsed["items"])
    total_cents = int(round(parsed["total"] * 100))
    return {
        "source": source,
        "items": items,
        "total_cents": total_cents,
        "items_sum_cents": sum(i["price_cents"] for i in items),
    }


@app.get("/api/contacts")
def contacts():
    return CONTACTS


@app.get("/api/status")
def status():
    return {"api_key": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.post("/api/receipts/parse")
async def receipts_parse(image: UploadFile = File(...)):
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Slika je prevelika (največ 15 MB).")
    try:
        parsed = parse_receipt(data)
    except ReceiptError as e:
        raise HTTPException(502, str(e)) from e
    # Slike ne shranjujemo: po branju ostane samo seznam postavk.
    return _receipt_response(parsed, "claude")


@app.get("/api/receipts/demo")
def receipts_demo():
    return _receipt_response(json.loads(DEMO_RECEIPT.read_text()), "demo")


class Item(BaseModel):
    id: str
    group_id: str
    name: str
    price_cents: int


class Bill(BaseModel):
    merchant: str = "Račun"
    items: list[Item]
    participants: list[str]
    assignments: dict[str, dict[str, int]]


def _summarize(bill: Bill) -> dict:
    """Strežnik sam izračuna deleže iz postavk; zneskom odjemalca ne zaupamo."""
    if PAYER not in bill.participants:
        raise HTTPException(400, "Plačnik mora biti v skupini.")
    unknown = [p for p in bill.participants if p not in CONTACTS_BY_ID]
    if unknown:
        raise HTTPException(400, f"Neznani kontakti: {unknown}")
    if any(i.price_cents < 0 for i in bill.items):
        raise HTTPException(400, "Cena postavke ne sme biti negativna.")
    items = [i.model_dump() for i in bill.items]
    try:
        breakdown = compute_breakdown(items, bill.participants, bill.assignments, PAYER)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    names = {i.id: i.name for i in bill.items}
    people = []
    for pid in bill.participants:
        parts = [{**part, "name": names[part["item_id"]]} for part in breakdown[pid]]
        people.append({
            "participant": CONTACTS_BY_ID[pid],
            "amount_cents": sum(p["cents"] for p in parts),
            "items": parts,
            "is_payer": pid == PAYER,
        })
    return {"people": people, "total_cents": sum(i.price_cents for i in bill.items)}


@app.post("/api/bills/summary")
def bills_summary(bill: Bill):
    return _summarize(bill)


@app.post("/api/bills/send")
def bills_send(bill: Bill):
    summary = _summarize(bill)
    created = []
    now = datetime.now().isoformat(timespec="minutes")
    for person in summary["people"]:
        if person["is_payer"] or person["amount_cents"] == 0:
            continue
        request = {
            "id": uuid.uuid4().hex[:8],
            "to": person["participant"],
            "from": CONTACTS_BY_ID[PAYER],
            "merchant": bill.merchant,
            "amount_cents": person["amount_cents"],
            "items": person["items"],
            "status": "čaka",
            "created_at": now,
        }
        REQUESTS.insert(0, request)
        created.append(request)
    return {"requests": created, "summary": summary}


@app.get("/api/requests")
def requests_list():
    return REQUESTS


@app.post("/api/requests/{request_id}/pay")
def requests_pay(request_id: str):
    for request in REQUESTS:
        if request["id"] == request_id:
            request["status"] = "plačano"
            return request
    raise HTTPException(404, "Zahtevek ne obstaja.")
