"""OCR vseh računov shrani v JSON (škatle + vrstice), da lahko pravila preizkušamo brez ponovnega OCR."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from reader.lines import build_lines
from reader.ocr import read_boxes

folder, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
data = {}
for path in sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}):
    boxes = read_boxes(path.read_bytes())
    data[path.name] = {"boxes": [b.__dict__ for b in boxes], "lines": build_lines(boxes)}
    print(path.name, len(boxes), flush=True)
out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
