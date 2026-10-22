# Branje računov z lokalnim modelom – plan

Ta dokument dopolnjuje poglavje 3 v [plan.md](plan.md). Odgovarja na vprašanje: ali lahko namesto Claude API račune beremo lokalno, z OCR v ONNX Runtime in majhnim LLM (Qwen3)?

**Kratek odgovor:** da, ampak z nekaj spremembami glede na prvotno idejo:

1. **Qwen3-4B-Instruct-2507 namesto Qwen3-0.6B.** 0.6B na naših računih ni pravilno prebral nobenega, 4B-Instruct-2507 pa vse, in je med preizkušenimi 4B modeli najhitrejši (glej meritve spodaj).
2. **LLM ne dobi surovih pozicij iz OCR.** Koda iz pozicij najprej sestavi vrstice in stolpce, model dobi urejeno besedilo.
3. **JSON izhod je vsiljen s shemo** (llama.cpp `json_schema`), zato je vedno veljaven.
4. **Koda preveri, kar model rad zamoči:** količine (z ceno na kos) in vsoto (s „Skupaj“).
5. **Claude API ostane kot stikalo** za primerjavo in kot rezerva, če lokalni model na demu ne bi deloval.

Glavni argument za lokalno pot je **zasebnost**: slika računa ne zapusti strežnika. Za banko je to močna zgodba v pitchu in prinaša točke pri kriteriju „varnost“ (tehnična izvedba, 20 točk).

---

## 1. Kaj smo izmerili

Poskus 22. 10. 2026 na prenosniku ekipe (Apple A18 Pro, **8 GB RAM**), na 5 računih iz `slike/racuni/`. Poženete ga s skriptom [backend/experiments/ocr_llm_experiment.py](backend/experiments/ocr_llm_experiment.py).

Postopek: RapidOCR (PP-OCRv6, ONNX Runtime) → vrstice po y-koordinati → Qwen3 prek `llama-server` z JSON shemo → primerjava vsote postavk s „Skupaj“.

| Model | Vsota se ujema | Tipične napake | Čas LLM na račun |
|---|---|---|---|
| Qwen3-0.6B (Q8) | **0 / 5** | „Skupaj“, „GOTOVINA“ in naslov trgovine šteje kot izdelke; Radler manjka | 2–8 s |
| Qwen3-1.7B (Q8) | **3 / 5** | količina 0 pri teži; 8 piv namesto 2 | 6–16 s |
| Qwen3-4B (Q4_K_M) | **5 / 5** | količine: 8 piv namesto 2, 30 iz imena „…30kos“ | 12–35 s |
| **Qwen3-4B-Instruct-2507** (Q4_K_M) | **5 / 5** | količine na dm računu: oznako DDV („2“) prebere kot količino | 10–31 s |
| Gemma 3 4B (Q4_K_M) | **1 / 5** | darilno kartico, DDV vrstico in „Kartica“ šteje kot izdelke; Radler 6,00 | 11–39 s |
| Qwen3-VL-4B (Q4_K_M), **brez OCR**, bere sliko | **4 / 5** | dm: 0,35 prebere kot 0,95; količina 0 pri teži; oznake DDV kot količine | 17–76 s |

Qwen3-VL bere sliko sam, zato ne potrebuje OCR. Imena prebere lepše (`Voelkel`, `vafliji`, `0%` namesto OCR-jevih `Voelke1`, `vaflii`, `O%`), vendar se zmoti pri ceni, kar je huje kot napaka v imenu. Je tudi 1,5–2,5-krat počasnejši od OCR + 2507.

Pri dm računu so številke `1` in `2` desno od cene **oznake stopnje DDV** (1 = 22 %, 2 = 9,5 %), ne količine. Vse količine so 1. To zmede vse modele in prav to ujame preverjanje količine v kodi (poglavje 2).

OCR sam (PP-OCRv6 v ONNX Runtime):
- **dobro:** pravilno prebere šumnike (`KRAČE PIŠČANČJE`, `Čebulni obročki`) in skoraj vse številke, običajno v 1–8 s na račun,
- **napake:** `9,00` → `00'6`, `Skupaj` → `Skupa,j`, okrasne zvezdice → kitajski znaki. Model 4B je `9,00` pravilno razbral iz konteksta, 1.7B in 0.6B nista,
- **pomnilnik:** ko je bil hkrati naložen še LLM, se je OCR zaradi pomanjkanja RAM upočasnil na 46–76 s. Na demu mora biti naložen samo en model.

Pravilne vrednosti smo ročno preverili za 4 račune (Spar, burgerji, Hotel Kras, dm). Pri ostalih dveh preverjamo samo, ali se vsota ujema. 5 računov je malo, zato so to zgodnji kazalci, ne končna ocena (glej korak 4 v poglavju 6).

---

## 2. Arhitektura

```
slika (.png/.jpg/.webp)
   │
   ▼
1. Predobdelava (Pillow)        poravnaj po EXIF, pomanjšaj na ≤ 1600 px, sivinska slika
   │
   ▼
2. OCR – RapidOCR, ONNX Runtime  škatle (x, y) + besedilo + zanesljivost
   │
   ▼
3. Sestavljanje vrstic (koda)    združi škatle z enako višino v vrstico, uredi po x,
   │                             stolpce loči z " | ", izpusti vrstice z nizko zanesljivostjo
   ▼
4. Qwen3-4B-Instruct-2507        poziv + vsiljena JSON shema, temperature 0 (llama-server)
   │
   ▼
5. Naknadna obdelava (koda)      količina: preveri qty × unit_price ≈ price, sicer popravi
   │                             izloči "Skupaj", "DDV", "Gotovina", "Vračilo" …
   ▼
6. Preverjanje                   Σ price ≈ total?  ne → 1 ponovni klic s povratno informacijo
   │                                                 še vedno ne → opozorilo v UI (že obstaja)
   ▼
JSON  { items: [{ name, quantity, price }], total }   ← enako kot plan.md 3.1
```

Izhod je **enak** kot zdaj iz Claude API. Frontendu in logiki deljenja zato ni treba spreminjati ničesar.

### Zakaj vrstice in ne surove pozicije
OCR vrne za vsako besedo štiri kote škatle. Če to v JSON-u pošljemo majhnemu modelu, bo moral sam ugotoviti, katere besede so v isti vrstici. Pri tem se zmoti in porabi veliko konteksta. To je preprosta geometrija, ki jo koda naredi brez napak (približno 20 vrstic, že v skriptu). Model dobi, kar človek vidi na računu:

```
Izdelek | Količina | Cena Popust | Znesek
KRAČE PIŠČANČJE IK | 0.796 | 5.79 | 2.23 | 2.38 B
MLETO MESO MEŠANO | 0.486 | 9.17 | 0.00 | 4.46 B
Skupa,j | EUR | 6.84
```

### Zakaj preverjanje količine v kodi
Vsi trije modeli so pri količini delali napake (zamenjajo jo z zneskom ali s številom v imenu). Zato v shemo dodamo `unit_price` (cena na kos) in koda odloči tako:
- če `quantity × unit_price ≈ price` → količina je prava,
- sicer če je `price / unit_price` celo število → to je količina,
- sicer `quantity = 1` (postavka se ne razbije na kose, uporabnik jo lahko razbije ročno).

`unit_price` uporabimo samo za to preverjanje. V izhodni JSON gre ista oblika kot doslej.

---

## 3. Primerjava možnosti

| Možnost | Zasebnost | Točnost | Hitrost na 8 GB | Delo | Ocena |
|---|---|---|---|---|---|
| **OCR ONNX + Qwen3-4B-Instruct-2507 + preverjanje** | slika ostane lokalno | 5/5 vsot (n = 5) | 12–38 s | srednje | **priporočeno** |
| OCR ONNX + Qwen3-4B (hibridni) | lokalno | 5/5 | 15–40 s | srednje | enako dober, nekoliko počasnejši |
| OCR ONNX + Gemma 3 4B | lokalno | 1/5 | 13–45 s | srednje | ne |
| OCR ONNX + Qwen3-1.7B | lokalno | 3/5 | 8–20 s | srednje | rezerva, če je 4B prepočasen |
| OCR ONNX + Qwen3-0.6B | lokalno | 0/5 | 3–10 s | srednje | ne |
| Claude API (že narejeno) | slika gre k ponudniku | ni izmerjeno (ni ključa) | pričakovano < 10 s | narejeno | za primerjavo in rezervo |
| Qwen3-VL-4B brez OCR | lokalno | 4/5 | 17–76 s | malo | ne: počasnejši in zmoti ceno; lepša imena niso vredna tega |
| Lasten fine-tuning (Donut, LoRA) | lokalno | — | — | veliko, ni podatkov | ne v času hackathona |

**Zakaj ne Qwen3-0.6B:** meritve zgoraj. Je premajhen, da bi ločil izdelke od vsot in plačila, kar je bistvo naloge.

**Zakaj ne treniramo:** imamo približno 22 računov. Za fine-tuning bi jih rabili stotine in več dni dela. Dober poziv, vsiljena shema in preverjanje v kodi so dosegli 5/5 brez treniranja.

---

## 4. Strojna oprema in demo

- Prenosnik ima 8 GB RAM. Qwen3-4B-Instruct-2507 Q4_K_M zasede približno 2,5 GB, OCR približno 0,5 GB. Na demu naj bo naložen **samo en LLM**, brez drugih zahtevnih aplikacij.
- Model **naložimo pred pitchem** in poženemo en „ogrevalni“ račun, da prvi pravi račun ni počasnejši.
- 15–40 s je za demo dolgo. Možnosti:
  - v UI prikažemo napredek po korakih („Berem besedilo …“, „Prepoznavam postavke …“), kar je tudi dober tehnični prikaz,
  - slike pomanjšamo pred OCR (≤ 1600 px), kar skrajša OCR,
  - če je še vedno prepočasno, preklopimo na Qwen3-1.7B ali na Claude s stikalom.
- Rezervni scenarij iz plan.md ostane: gumb „Uporabi demo račun“ in ročni vnos.

---

## 5. Implementacija v našem repozitoriju

```
backend/
├── parse_receipt.py        # izbere bralnik glede na RECEIPT_READER=local|claude
├── reader/
│   ├── ocr.py              # RapidOCR (ONNX Runtime) + predobdelava slike
│   ├── lines.py            # škatle → vrstice s stolpci
│   ├── local_llm.py        # klic llama-server z JSON shemo, ponovni klic s povratno informacijo
│   └── postprocess.py      # preverjanje količine, izločanje "Skupaj/DDV/Gotovina", številke
├── experiments/
│   └── ocr_llm_experiment.py     # poskus iz poglavja 1
└── eval.py                 # metrike na vseh računih: local proti claude
```

Zagon lokalnega modela (v ločenem terminalu, pred backendom):

```bash
brew install llama.cpp
llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M --port 8081 -c 8192 --jinja
```

Backend:

```bash
.venv/bin/pip install rapidocr onnxruntime
RECEIPT_READER=local LLM_URL=http://127.0.0.1:8081 .venv/bin/uvicorn main:app --port 8000
```

---

## 6. Koraki

1. [x] `reader/ocr.py` + `reader/lines.py` (prenos iz `experiments/ocr_llm_experiment.py`), s predobdelavo slike.
2. [x] `reader/local_llm.py` s shemo, ki vsebuje `unit_price`, in ponovnim klicem, ko se vsota ne ujema.
3. [x] `reader/postprocess.py` + testi (količina, izločanje vsot, `00'6` ipd.).
4. [ ] Ročno označiti pravilen JSON za vseh ~22 računov (`data/receipts/labels/`). Brez tega ne vemo, kako dobri smo.
5. [ ] `eval.py`: tabela *lokalno (1.7B / 4B) proti Claude* za pitch: % ujemanja vsote, % pravilnih postavk, čas.
6. [x] Stikalo `RECEIPT_READER` in napredek po korakih v UI.
7. [x] Poskus z vision modelom (Qwen3-VL-4B) brez OCR: 4/5, počasnejši, zato ostanemo pri OCR + 2507.

### Rezultat vgrajenega bralnika (22. 10. 2026)

Isti 5 računov prek `POST /api/receipts/parse` (OCR + Qwen3-4B-Instruct-2507 + naknadna obdelava):

| Račun | Vsota | Količine | OCR | LLM |
|---|---|---|---|---|
| Spar (teža, popust) | ✓ 6,84 | ✓ | 2,6 s | 8,5 s |
| Burgerji (Radler 2x, OCR `00'6`) | ✓ 32,40 | ✓ | 1,0 s | 14,2 s |
| dm (oznake DDV desno) | ✓ 50,10 | ✓ vse 1 | 4,2 s | 24,9 s |
| 860096… | ✓ 20,55 | ni preverjeno | 2,9 s | 5,8 s |
| Hotel Kras (2x pivo) | ✓ 14,40 | ✓ | 2,3 s | 8,7 s |

Količine na dm računu je popravila koda, ne model: znesek mora biti napisan na računu, količina ≥ 2 pa potrebuje dokaz (napisano ceno kosa ali oznako `2x`). Glej `reader/postprocess.py` in `test_reader.py`.

### Hitrost: pravila najprej, model samo kot rezerva (22. 10. 2026)

Prva različica (model napiše vse postavke kot JSON) je pri dolgem računu potrebovala ~170 s: model na tem prenosniku piše ~15 žetonov/s, odgovor za dolg račun pa ima > 1.000 žetonov. Zato zdaj:

1. **Pravila (brez modela):** koda sama prebere postavke med glavo tabele in vrstico „Skupaj“. Če se vsota ujema, je konec, čas = samo OCR.
2. **Model kot rezerva**, samo pri računih z < 10 postavkami, kjer se vsota ne ujema. Vrne le številke vrstic z izdelki (~2 žetona na postavko); imena in zneske vzame koda iz besedila.

Na vseh 63 računih v `slike/racuni/`:

| | Vrednost |
|---|---|
| Vsota se ujema | **38 / 63** (60 %) |
| Prebrano samo s pravili | 35 računov |
| Povprečen čas | **7 s** |
| Najdaljši čas | ~11 s (prej 31 s, preden smo pri dolgih računih preskočili model) |

Neujemanja so večinoma pri majhnih računih iz lokalov (1–3 postavke, druga postavitev) in pri posameznih napačno prebranih številkah na dolgih računih. Uporabnik razliko vidi na zaslonu „Preveri postavke“ in jo popravi. Merjenje: `backend/experiments/speed_all.py`.

### Tabela kot CSV in popravek po vsoti (22. 10. 2026)

Pregled neujemanj je pokazal, da je glavni vzrok **en pokvarjen znesek v vrstici** (`∠69` namesto `6,97`, manjkajoč znesek pri teži), ne model. Zato zdaj:

1. **Tabela kot CSV** (`reader/table.py`): vsako številko pripišemo stolpcu iz glave (Količina, Cena, Popust, Znesek) po položaju x. Ker velja znesek = količina × cena − popust, pokvarjen ali manjkajoč znesek izračunamo iz ostalih stolpcev.
2. **Popravek po vsoti** (`reader/repair.py`): izmed prebranega in izračunanega zneska izberemo kombinacijo, ki da točno „Skupaj“. Če manjka en sam znesek, je to razlika do „Skupaj“.
3. Storno (`-1 | 30,99 | -30,99`) odstrani izdelek, popust z minusom zmanjša prejšnjo postavko, ključne besede tudi brez šumnikov (`ZA PLACILO`, `SKUPAJEUR`, `MEDUZBROJ`), stopnja DDV `(9,50%)` ni cena.

| | Prej | Zdaj |
|---|---|---|
| Vsota se ujema (brez modela) | 37 / 63 | **56 / 63** |
| Prebrano s tabelo | – | 45 računov |

Preostalih 7: 3 potrdila kartice ali parkirnine brez postavk, 2 nečitljivi sliki, 2 računa iz lokalov z zelo pokvarjenim OCR. Te uporabnik vnese ali popravi ročno. Preizkus brez OCR: `backend/experiments/eval_cache.py` (OCR shrani `experiments/dump_ocr.py`).

## 7. Tveganja

| Tveganje | Kaj naredimo |
|---|---|
| Na demu je prepočasno | ogrevanje, manjše slike, preklop na 1.7B ali Claude |
| Zmanjka RAM | naložen samo en model, zaprte druge aplikacije |
| Model prebere napačno | preverjanje vsote + opozorilo v UI + ročni popravek (že obstaja) |
| Nov tip računa, ki ga nismo videli | eval na vseh ~22 računih pred demom; demo z računom, ki deluje |

## 8. Za pitch

- „Slika računa ne zapusti strežnika: OCR in jezikovni model tečeta lokalno.“
- „Model ne odloča sam: koda preveri količine in vsoto, uporabnik potrdi.“
- Tabela iz `eval.py`: lokalni model proti Claude, na naših pravih računih.
