# Flik Razdeli račun

Proof of concept za Bankart Hackathon 2026: naložiš sliko računa, Claude prebere postavke, ti določiš, kdo je imel kaj, in vsakemu pošlješ (mock) Flik zahtevek. Plan je v [plan.md](plan.md).

## Zagon

Backend (port 8000):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # brez ključa deluje samo demo račun
.venv/bin/uvicorn main:app --port 8000 --reload
```

Frontend (port 5173), v drugem terminalu:

```bash
cd frontend
npm install
npm run dev
```

Odpri http://localhost:5173. Pogled prejemnika (kaj vidi prijatelj, ki dobi zahtevek) je na http://localhost:5173/?view=prejemnik, najbolje v drugem oknu.

Model lahko zamenjaš z `CLAUDE_MODEL=claude-sonnet-5-5` (privzeto `claude-opus-5-5`).

## Testi

```bash
cd backend && .venv/bin/pytest -q
```
