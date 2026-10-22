"""FastAPI strežnik za Flik Razdeli račun (proof of concept, vse v pomnilniku)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from parse_receipt import READER, ReceiptError, is_ready, parse_receipt
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
        "timings": parsed.get("timings"),
    }


@app.get("/api/contacts")
def contacts():
    return CONTACTS


class NewContact(BaseModel):
    phone: str


def _normalize_phone(raw: str) -> str | None:
    """'031 234 567', '+386 31 234 567', '00386...' -> '+38631234567'; None, če ni številka."""
    digits = re.sub(r"[\s\-/()]", "", raw)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    elif digits.startswith("0"):
        digits = "+386" + digits[1:]
    elif not digits.startswith("+"):
        digits = "+386" + digits
    return digits if re.fullmatch(r"\+\d{8,15}", digits) else None


def _format_phone(phone: str) -> str:
    if phone.startswith("+386") and len(phone) == 12:
        return f"+386 {phone[4:6]} {phone[6:9]} {phone[9:]}"
    return phone


@app.post("/api/contacts")
def contacts_add(body: NewContact):
    """Doda osebo, ki je ni v imeniku, samo prek telefonske številke."""
    phone = _normalize_phone(body.phone)
    if phone is None:
        raise HTTPException(400, "To ni veljavna telefonska številka.")
    contact_id = f"tel{phone}"
    if contact_id not in CONTACTS_BY_ID:
        local = "0" + phone[4:] if phone.startswith("+386") else phone
        name = f"{local[:3]} {local[3:6]} {local[6:]}" if len(local) == 9 else local
        contact = {"id": contact_id, "name": name, "phone": _format_phone(phone), "color": "#ff7a8a"}
        CONTACTS.append(contact)
        CONTACTS_BY_ID[contact_id] = contact
    return CONTACTS_BY_ID[contact_id]


@app.get("/api/status")
def status():
    return {"reader": READER, "ready": is_ready()}


@app.post("/api/receipts/parse")
async def receipts_parse(image: UploadFile = File(...)):
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Slika je prevelika (največ 15 MB).")
    try:
        # Lokalni model bere do ~40 s; v niti, da strežnik medtem odgovarja na druge zahteve.
        parsed = await run_in_threadpool(parse_receipt, data)
    except ReceiptError as e:
        raise HTTPException(502, str(e)) from e
    # Slike ne shranjujemo: po branju ostane samo seznam postavk.
    return _receipt_response(parsed, READER)


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
