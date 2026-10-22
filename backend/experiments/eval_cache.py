"""Brez OCR in brez modela: tabela + pravila na shranjenem OCR (experiments/dump_ocr.py).
Izpiše, pri katerih računih se vsota ujema, in neujemanja za pregled."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from reader.lines import build_rows
from reader.local import parse_rows
from reader.ocr import Box
from reader.postprocess import sum_matches

data = json.loads(pathlib.Path(sys.argv[1]).read_text())
verbose = "-v" in sys.argv
ok = 0
for name, v in data.items():
    rows = build_rows([Box(**b) for b in v["boxes"]])
    receipt, _ = parse_rows(rows)
    s = round(sum(i["price"] for i in receipt["items"]), 2)
    match = sum_matches(receipt)
    ok += match
    if not match or verbose:
        print(f"{'OK     ' if match else 'RAZLIKA'} {s:8.2f} / {receipt['total']:8.2f}  {receipt.get('method', 'rules'):5}  {name[:40]}")
print(f"\nvsota OK: {ok}/{len(data)}")
