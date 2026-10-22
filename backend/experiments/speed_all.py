"""Poženi lokalni bralnik na vseh računih in izpiši čas ter ujemanje vsote."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from reader import local
from reader.errors import ReceiptError

folder = pathlib.Path(sys.argv[1])
times, ok = [], 0
files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
for path in files:
    start = time.perf_counter()
    try:
        r = local.read(path.read_bytes())
        s = round(sum(i["price"] for i in r["items"]), 2)
        match = abs(s - r["total"]) < 0.005
        status = f"{'OK     ' if match else 'RAZLIKA'} {s:7.2f} / {r['total']:7.2f}  {len(r['items']):2d} postavk  ocr {r['timings']['ocr_ms']/1000:4.1f}s llm {r['timings'].get('llm_ms', 0)/1000:4.1f}s {r['timings']['method']}"
        ok += match
    except ReceiptError as e:
        status = f"NAPAKA  {e}"
    took = time.perf_counter() - start
    times.append(took)
    print(f"{took:5.1f}s  {status}  {path.name[:28]}", flush=True)
print(f"\nvsota OK: {ok}/{len(files)}   čas: povprečje {sum(times)/len(times):.1f}s, največ {max(times):.1f}s")
