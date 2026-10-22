"""Bralnik s Claude API: slika → { items: [{name, quantity, price}], total }."""

from __future__ import annotations

import base64
import io
import json
import os

import anthropic
from PIL import Image, ImageOps

from .errors import ReceiptError

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MAX_SIDE = 2000

PROMPT = """Na sliki je račun iz trgovine ali lokala (običajno v slovenščini ali hrvaščini).
Preberi postavke, ki jih je kupec plačal, in končni znesek.

Pravila:
- Vrni samo kupljene izdelke. Izpusti vmesne vsote, DDV tabelo, način plačila, gotovino in vračilo.
- `name`: ime izdelka, kot piše na računu.
- `quantity`: število kosov kot celo število (npr. "2x4,50" → 2). Izdelki, ki se tehtajo (npr. 0,796 kg), imajo quantity 1.
- `price`: znesek celotne vrstice, ki se šteje v vsoto. Če ima vrstica popust, ga že odštej.
- Količina in cena sta lahko v vrstici pod ali nad imenom izdelka; pripadata temu izdelku.
- `total`: končni znesek za plačilo.
- Decimalno vejico pretvori v število (8,00 → 8.00)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "price": {"type": "number"},
                },
                "required": ["name", "quantity", "price"],
                "additionalProperties": False,
            },
        },
        "total": {"type": "number"},
    },
    "required": ["items", "total"],
    "additionalProperties": False,
}


def _prepare_image(data: bytes) -> str:
    """Poravna, pomanjša in pretvori sliko v JPEG (base64), da ostane pod omejitvijo API-ja."""
    try:
        image = Image.open(io.BytesIO(data))
    except Exception as e:
        raise ReceiptError("Slike ni mogoče odpreti. Naloži JPG, PNG ali WEBP.") from e
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=88)
    return base64.standard_b64encode(out.getvalue()).decode("utf-8")


def read(data: bytes) -> dict:
    image_b64 = _prepare_image(data)
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        )
    except anthropic.AuthenticationError as e:
        raise ReceiptError("API ključ ni veljaven. Preveri ANTHROPIC_API_KEY.") from e
    except anthropic.RateLimitError as e:
        raise ReceiptError("Preveč zahtev na API. Poskusi čez nekaj sekund.") from e
    except anthropic.APIStatusError as e:
        raise ReceiptError(f"Napaka API-ja ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ReceiptError("Ni povezave z API-jem. Preveri internet.") from e

    if response.stop_reason == "refusal":
        raise ReceiptError("Model je zavrnil branje te slike.")
    if response.stop_reason == "max_tokens":
        raise ReceiptError("Račun je predolg za branje.")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise ReceiptError("Model ni vrnil rezultata.")
    return json.loads(text)
