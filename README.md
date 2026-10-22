# Flik Razdeli račun

Proof of concept za Bankart Hackathon 2026: slikaš račun, lokalni model prebere postavke, ti določiš, kdo je imel kaj, in vsakemu pošlješ (mock) Flik zahtevek. Plan je v [plan.md](plan.md), izbira modela v [model_plan.md](model_plan.md).

## Zagon

Račune bere lokalno: OCR (RapidOCR v ONNX Runtime) + Qwen3-4B-Instruct-2507 v llama.cpp. Slika ne zapusti računalnika.

1. Model (port 8081). Ob prvem zagonu prenese ~2,5 GB:

```bash
brew install llama.cpp
llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M --port 8081 -c 8192 --jinja
```

2. Backend (port 8000), v drugem terminalu:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000 --reload --reload-exclude '.venv/*'
```

Namesto lokalnega modela lahko uporabiš Claude API: `RECEIPT_READER=claude ANTHROPIC_API_KEY=sk-ant-... .venv/bin/uvicorn main:app --port 8000`.

3. Frontend (port 5173), v tretjem terminalu:

```bash
cd frontend
npm install
npm run dev
```

Odpri http://localhost:5173. Pogled prejemnika (kaj vidi prijatelj, ki dobi zahtevek) je na http://localhost:5173/?view=prejemnik, najbolje v drugem oknu.

Na računalniku z 8 GB RAM naj bo naložen samo ta en model; branje računa traja 10–30 s.

## Testi

```bash
cd backend && .venv/bin/pytest -q
```
