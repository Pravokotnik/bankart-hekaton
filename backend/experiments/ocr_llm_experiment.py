"""OCR (RapidOCR/ONNX) -> vrstice po y -> Qwen3 prek llama-server z JSON shemo -> preverjanje vsote."""
import base64, io, json, os, sys, time, urllib.request
from PIL import Image, ImageOps

# MODE=ocr (privzeto): OCR -> besedilo -> LLM.  MODE=vision: slika gre neposredno v model.
MODE = os.environ.get("MODE", "ocr")
# Samo hibridni Qwen3 modeli poznajo /no_think.
NO_THINK = os.environ.get("NO_THINK", "1") == "1"

SCHEMA = {"type": "object", "properties": {
    "items": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "quantity": {"type": "integer"}, "price": {"type": "number"}},
        "required": ["name", "quantity", "price"]}},
    "total": {"type": "number"}}, "required": ["items", "total"]}

PROMPT = """Spodaj je besedilo računa, prebrano z OCR, vrstica za vrstico (stolpci ločeni z " | ").
Vrni JSON s kupljenimi izdelki in končnim zneskom.
- Samo kupljeni izdelki: brez glave, vmesnih vsot, DDV tabele, plačila.
- name: ime izdelka. quantity: število kosov (celo število, "2x4,50" pomeni 2; teža v kg pomeni 1).
- price: znesek celotne vrstice (stolpec Znesek), po popustu.
- Vrstica s količino in ceno je lahko pod imenom izdelka in mu pripada.
- total: končni znesek za plačilo (Skupaj / Za plačilo).

Račun:
"""

def lines(result):
    boxes = sorted(zip(result.boxes, result.txts), key=lambda b: (b[0][0][1] + b[0][2][1]) / 2)
    rows, cur, cur_y = [], [], None
    for box, txt in boxes:
        y = (box[0][1] + box[2][1]) / 2
        h = abs(box[2][1] - box[0][1])
        if cur and abs(y - cur_y) > h * 0.6:
            rows.append(cur); cur = []
        if not cur: cur_y = y
        cur.append((box[0][0], txt))
    if cur: rows.append(cur)
    return [" | ".join(t for _, t in sorted(r)) for r in rows]

def image_b64(path, max_side=1280):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()

def ask(text, port, image=None):
    suffix = " /no_think" if NO_THINK else ""
    if image:
        content = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}},
                   {"type": "text", "text": PROMPT.replace("Spodaj je besedilo računa, prebrano z OCR, vrstica za vrstico (stolpci ločeni z \" | \").", "Na sliki je račun.") + suffix}]
    else:
        content = PROMPT + text + suffix
    body = {"messages": [{"role": "user", "content": content}],
            "temperature": 0, "response_format": {"type": "json_schema", "json_schema": {"schema": SCHEMA}}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=300))
    return json.loads(out["choices"][0]["message"]["content"])

port = int(sys.argv[1])
if MODE == "ocr":
    from rapidocr import RapidOCR
    eng = RapidOCR()
for path in sys.argv[2:]:
    t0 = time.time()
    if MODE == "ocr":
        text = "\n".join(lines(eng(path))); t1 = time.time(); data = ask(text, port)
    else:
        img = image_b64(path); t1 = time.time(); data = ask("", port, image=img)
    t2 = time.time()
    s = round(sum(i["price"] for i in data["items"]), 2)
    print(f"== {path.split('/')[-1][:30]} OCR {t1-t0:.1f}s LLM {t2-t1:.1f}s  vsota {s} / total {data['total']} {'OK' if abs(s-data['total'])<0.01 else 'NAPAKA'}")
    for i in data["items"]: print("   ", i)
