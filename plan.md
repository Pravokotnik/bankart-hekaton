# Flik Razdeli račun – plan projekta

**Hackathon:** Bankart Hackathon 2026, Izziv 1 – *Plačevanje brez trenja*
**Ideja v enem stavku:** V Fliku slikaš račun, aplikacija sama prebere izdelke in cene, ti pa samo s klikom določiš, kdo je imel kaj, in vsakemu pošlješ Flik zahtevek za točen znesek.

---

## 0. Kako nas ocenjujejo (in kaj to pomeni za plan)

| Kriterij | Točke | Kaj moramo pokazati |
|---|---|---|
| Zastavljen problem | 15 | Pogovori z uporabniki: kako danes delijo račune, koliko časa jim to vzame, kje se zatakne |
| Inovativnost | 35 | Ne le „deli na enake dele“, ampak deljenje po izdelkih, deljenje enega izdelka med več ljudi, vse v enem toku in neposredno do Flik zahtevka |
| Tehnična izvedba | 20 | Prototip, ki deluje; premišljena arhitektura; **varnost in zasebnost** (slike računov, kontakti, API ključi) |
| Vrednost rešitve | 20 | Merljivo: npr. „iz ~3 min računanja in tipkanja na ~30 s“ |
| Pitch & demo (5 min) | 10 | Tekoč demo v živo s pravim računom, z rezervnim scenarijem |

Največ točk je za inovativnost in za kombinacijo tehnične izvedbe in vrednosti, zato mora biti jedro (slikaj → poklikaj → zahtevaj) res dobro izvedeno.

---

## 1. Problem in raziskava uporabnikov

### 1.1 Hipoteza
Ko gre skupina na večerjo, pijačo ali v trgovino, račun plača ena oseba. Potem mora:
1. ročno sešteti, kdo je imel kaj (pogosto na pamet ali s kalkulatorjem),
2. razdeliti skupne stvari (pica za 3, steklenica vina za 4),
3. vsakemu posebej poslati zahtevek z ročno vpisanim zneskom.

Posledice: izgubljen čas, napake, nerodnost („pa saj je samo 2 €…“), zato ljudje pogosto delijo kar na enake dele, kar je nepravično.

### 1.2 Kaj moramo preveriti (pred hackathonom in med njim)
- **Intervjuji: 8–15 ljudi** (študenti, sodelavci, natakarji). Vprašanja:
  - Kako ste nazadnje delili račun? Koliko časa je trajalo?
  - Ali delite na enake dele ali po porabi? Zakaj?
  - Ali uporabljate Flik ali kaj drugega (Revolut, Splitwise, gotovina)?
  - Kaj vas najbolj moti?
- **Natakarji / lokali:** kako pogosto gosti zahtevajo ločene račune in koliko časa to vzame osebju.
- **Kratka anketa** (Google Forms) za nekaj številk za pitch, npr. „X % deli na enake dele, čeprav ni pošteno“.
- **Konkurenca:** Splitwise, Tricount, Revolut „Split bill“. Ključna razlika: pri nas sta skeniranje in plačilo **v isti aplikaciji**, ki jo ljudje že uporabljajo za plačila v Sloveniji, in ni treba nikamor prepisovati zneskov.

**Rezultat:** 1 diapozitiv s citati in številkami za pitch.

---

## 2. Uporabniška izkušnja (UX tok)

```
Domov ──► [Razdeli račun] ──► Kamera / naloži sliko
                                   │
                                   ▼
                        Pregled prebranih postavk
                        (popravi ime in ceno;
                         preveri, da se vsota ujema s "Skupaj")
                                   │
                                   ▼
                        Dodaj ljudi v skupino
                        (izbira iz imenika, kot pri "Zahtevaj")
                                   │
                                   ▼
                        Dodeli izdelke
                        (tapni izdelek → tapni osebe;
                         ena oseba / več oseb / "vsi")
                                   │
                                   ▼
                        Povzetek: kdo dolguje koliko
                        (+ kaj je kdo imel)
                                   │
                                   ▼
                        [Pošlji zahtevke] ──► Flik zahtevek vsaki osebi
```

### 2.1 Zasloni
1. **Domov:** obstoječi Flik zaslon (Skeniraj / Pošlji / Zahtevaj) + nov gumb **Razdeli račun**.
2. **Zajem računa:** kamera (na telefonu) ali nalaganje slike; prikaz nalaganja med branjem.
3. **Pregled postavk:** seznam `ime · cena`. Izdelki z več kosi so v eni vrstici z oznako količine (`Pivo  ×2  8,00`), ki jo lahko razširiš na posamezne kose (glej 3.4). Vsako vrstico je mogoče urediti, izbrisati ali dodati. Na dnu `Vsota postavk` proti `Skupaj na računu`; če se ne ujemata, opozorilo.
4. **Skupina:** izbira kontaktov (kopija Flikovega zaslona „Izberi kontakt“ z iskalnikom in kljukicami). Jaz sem vedno v skupini.
5. **Dodeljevanje (jedro):**
   - na vrhu vrstica z avatarji oseb (barvni krogi z inicialkami, kot v Fliku),
   - **način A:** izbereš osebo, nato tapaš njene izdelke (hitro pri večjih skupinah),
   - **način B:** tapneš izdelek in v listu izbereš osebe,
   - gumb **„Vsi“** za skupne stvari (npr. kruh, voda),
   - izdelki z več kosi so privzeto **strnjeni** (`Pivo ×2`). Dodelitev strnjene vrstice velja za vse kose (npr. Ana in Miha si delita obe pivi). S tapom na `×2` (ali puščico) vrstico **razširiš** na `Pivo` in `Pivo` ter vsak kos dodeliš drugi osebi; s ponovnim tapom jo spet **strneš**,
   - strnjena vrstica, katere kosi so dodeljeni različnim osebam, pokaže avatarje vseh teh oseb,
   - nedodeljeni izdelki so jasno označeni; ne moreš naprej, dokler niso vsi dodeljeni (ali jih ne označiš kot „moje“).
6. **Povzetek:** kartica za vsako osebo z zneskom in seznamom izdelkov.
7. **Pošiljanje:** potrdi → nastanejo zahtevki → v razdelku *Zahtevki* so vidni s statusom (čaka / plačano).
8. **Prejemnik (bonus):** kaj vidi oseba, ki dobi zahtevek: znesek **in razčlenitev**, kaj je imela, zato ni prepirov.

---

## 3. Branje računov (Claude API)

Ne treniramo lastnega modela. Sliko računa pošljemo **Claude API-ju** (vision) in dobimo nazaj:
- **ime izdelka**,
- **število kosov** (`2x pivo` → 2),
- **ceno vrstice** (končna cena, že po morebitnem popustu),
- **končno ceno računa** (`Skupaj`).

### 3.1 Kaj vrne API
Uporabimo strukturiran izhod (tool use z JSON shemo), da ni treba ročno razčlenjevati besedila:

```json
{
  "items": [
    { "name": "Nefiltrirano pivo 0,5L", "quantity": 2, "price": 8.00 },
    { "name": "Piščančje krače", "quantity": 1, "price": 2.38 }
  ],
  "total": 14.40
}
```

### 3.2 Poziv
V pozivu modelu na kratko povemo:
- vrni samo postavke, ki jih je kupec plačal (brez vmesnih vsot, DDV tabele, gotovine, vračila),
- `quantity` je število kosov (celo število); izdelki, ki se tehtajo (npr. `0,796 kg`), imajo `quantity: 1`,
- `price` je znesek celotne vrstice, ki se šteje v vsoto (če je popust, ga že odštej),
- decimalno vejico pretvori v število (`8,00` → `8.00`),
- ime izdelka prepiši, kot piše na računu.

### 3.3 Preverjanje v aplikaciji
Na zaslonu *Pregled postavk* prikažemo `Vsota postavk` proti `Skupaj na računu`. Če se ne ujemata, uporabnik vidi opozorilo in postavko ročno popravi. Ni dodatnih klicev ali logike.

### 3.4 Razbijanje na kose
Vsako vrstico s `quantity > 1` backend razbije na `quantity` ločenih kosov, vsakega s ceno enega kosa. Kosi iste vrstice imajo skupen `group_id`:

```
{ "Pivo", quantity: 2, price: 8.00 }  →  Pivo 4,00   Pivo 4,00   (group_id: g1)
```

V UI so kosi iste skupine prikazani **strnjeno** kot ena vrstica z oznako `×2`, ki jo lahko razširiš in spet strneš:

```
▸ Pivo           ×2    8,00        (strnjeno)

▾ Pivo           ×2    8,00        (razširjeno)
    Pivo               4,00   [Ana]
    Pivo               4,00   [Miha]
```

- Strnjeno: dodelitev se zapiše na vse kose skupine.
- Razširjeno: vsak kos dodeliš posebej.
- Strnjevanje je samo prikaz; podatki so vedno shranjeni po kosih, zato se pri strnjevanju dodelitve ne izgubijo.
- Ceno delimo v centih; če se ne deli točno (npr. 10,00 € / 3 kosi), dobi prvi kos odvečni cent (3,34 + 3,33 + 3,33), da je vsota enaka ceni vrstice.
- Razbijanje naredi backend, ne model, zato je vedno pravilno.

### 3.5 Implementacija
- Ena funkcija na backendu: `parse_receipt(image) → { items, total }`, ki vrne že razbite postavke.
- API ključ je samo na backendu.
- Za demo pripravimo nekaj računov iz `slike/racuni/` in en vnaprej shranjen rezultat kot rezervo, če API odpove.

---

## 4. Logika deljenja

### 4.1 Model podatkov
```
Bill        { id, image, merchant, date, total, items[], participants[], payer }
Item        { id, group_id, name, price }   # en kos; group_id poveže kose iste vrstice
Participant { id, name, phone, color, isMe }
Assignment  { item_id, participant_id, shares }   # shares = delež (privzeto 1)
```

### 4.2 Pravila
- Vsaka postavka ima eno ali več dodelitev. Znesek postavke se razdeli **sorazmerno z `shares`**. Privzeto ima vsak 1 delež, torej enako; opcijsko 2:1 (npr. nekdo je pojedel 2 od 3 kosov pice).
- Postavke so že razbite na posamezne kose (glej 3.4), zato vsak kos dodelimo posebej.
- Popust ali napitnina na ravni računa se razdeli **sorazmerno** z vsoto posameznika.
- **Računamo v centih (integer)**, nikoli v float. Ostanek pri deljenju (npr. 10,00 € / 3) razdelimo z metodo *največjega ostanka*, da je vsota vseh deležev **točno** enaka računu. Pravilo mora biti deterministično, npr. odvečni cent dobi plačnik.
- Plačnik (jaz) ne dobi zahtevka; njegov delež samo prikažemo.

### 4.3 Testi (obvezno, ker gre za denar)
- 10,00 € / 3 osebe → 3,34 + 3,33 + 3,33, vsota je 10,00,
- postavka z deleži 2:1,
- razbijanje `2x pivo, 8,00` → dve postavki po 4,00; `3 kosi, 10,00` → 3,34 + 3,33 + 3,33,
- sorazmerna razdelitev popusta,
- nobena oseba ne dobi negativnega zneska; vsota zahtevkov + moj delež = `total`.

---

## 5. Web app, ki posnema Flik

### 5.1 Tehnologije (predlog)
| Del | Izbira | Zakaj |
|---|---|---|
| Frontend | **React + Vite + TypeScript**, Tailwind | hitro, mobilni prikaz, ekipa ga verjetno pozna |
| Mobilnost | PWA / mobilni brskalnik, `<input type="file" accept="image/*" capture="environment">` | kamera na telefonu brez nativne aplikacije |
| Backend | **FastAPI (Python)** | preprost, hiter za prototip |
| Branje računov | Claude API (vision, strukturiran izhod) | glej poglavje 3 |
| Shramba | v pomnilniku / SQLite | za demo dovolj |
| „Flik plačila“ | **mock**: zahtevki in transakcije v bazi, simuliran status „plačano“ | pravega Flik API-ja nimamo |
| Deploy | Vercel (frontend) + Render/Fly.io (backend) ali vse lokalno + ngrok | demo na pravem telefonu |

### 5.2 Struktura repozitorija
```
bankart-hekaton/
├── plan.md
├── navodila/                 # navodila hackathona
├── slike/flik/               # referenčni izgled Flika
├── slike/racuni/            # testni računi za demo
├── backend/
│   ├── main.py               # FastAPI: /api/receipts/parse, /api/bills, /api/requests
│   ├── parse_receipt.py      # slika → { items, total } prek Claude API
│   └── split.py              # logika deljenja + testi
└── frontend/
    └── src/
        ├── screens/          # Home, Scan, ReviewItems, Group, Assign, Summary, Requests
        └── components/       # FlikHeader, BottomNav, ContactRow, Avatar, ItemRow
```

### 5.3 Videz
- Kopiramo Flikov slog s posnetkov v `slike/flik/`: temno zeleno-siva podlaga, svetlo zeleni gumbi, zaobljene kartice, spodnja navigacija (*Domov / Transakcije / Zahtevki / Nastavitve*), krogi z inicialkami za kontakte.
- Opomba: posnetki so iz aplikacije OTP banke, ideja pa je za NLB Flik. Flik je skupna storitev (Bankart), zato v demu uporabimo **nevtralen „Flik“ videz** brez logotipa konkretne banke ali pa logotip banke, ki jo predstavljamo.
- Imenik: za demo **izmišljeni kontakti** (ne pravi podatki iz telefonov).

### 5.4 API
```
POST /api/receipts/parse     multipart image → { items: [{name, price}], total }   # postavke že razbite na kose
POST /api/bills              ustvari račun s postavkami in udeleženci
PUT  /api/bills/{id}/assign  shrani dodelitve
GET  /api/bills/{id}/summary znesek na osebo
POST /api/bills/{id}/send    ustvari mock Flik zahtevke
GET  /api/requests           seznam zahtevkov (za zaslon Zahtevki)
```

---

## 6. Varnost in zasebnost (del ocene „Tehnična izvedba“)

V pitchu namenimo temu en diapozitiv:
- **API ključi** samo na backendu, nikoli v frontendu.
- **Slike računov:** obdelamo in zavržemo; ne shranjujemo jih dlje, kot je potrebno. Po želji pred pošiljanjem zameglimo spodnji del (zadnje cifre kartice).
- **Kontakti:** ostanejo na napravi; strežnik dobi samo izbrane telefonske številke za zahtevke (kot v Fliku danes).
- **Avtorizacija plačila:** zahtevek ne prenese denarja; prejemnik ga še vedno potrdi v svoji Flik aplikaciji (obstoječi varnostni mehanizmi banke ostanejo).
- **Integriteta zneskov:** strežnik sam izračuna deleže iz postavk; ne zaupa zneskom, ki jih pošlje odjemalec.
- **Proti zlorabi:** omejitev števila zahtevkov, opozorilo, če je vsota zahtevkov večja od računa.
- **GDPR:** podatki na računu (natakar, lokal) so osebni ali poslovni podatki, zato jih ne hranimo po nepotrebnem.

---

## 7. Ideje za dodatno inovativnost (če ostane čas)

Po prioriteti:
1. **Razčlenitev pri prejemniku:** zahtevek vsebuje „tvoje postavke“, ne le znesek.
2. **Napitnina z enim drsnikom** (0 / 5 / 10 %), sorazmerno razdeljena.
3. **Deljenje v živo:** vsak udeleženec na svojem telefonu (prek povezave ali QR) sam označi, kaj je imel. Plačniku ni treba klikati za vse.
4. **Zapomni si skupino** („Cimri“, „Petek bar“) za ponovno uporabo.
5. **QR koda davčno potrjenega računa (ZOI/EOR):** možnost preverjanja pristnosti računa ali zaznave dvojnega skeniranja. *Treba je preveriti, kaj točno vsebuje QR (verjetno ZOI, davčno številko in čas, ne pa postavk).*
6. **Glasovni ukaz:** „Ana in jaz sva si delila pico.“

---

## 8. Časovnica in prioritete

Ker trajanje hackathona še ni določeno, plan razdelimo na **faze z jasnim MVP**. Če zmanjka časa, se ustavimo za črto MVP in demo še vedno deluje.

### Faza 0: pred hackathonom
- [ ] Zbrati nekaj raznolikih računov za demo (že v `slike/racuni/`).
- [ ] Intervjuji in anketa (glej 1.2).
- [ ] Fotografirati še manjkajoče Flik zaslone (Zahtevaj: vnos zneska, potrditev, Transakcije).
- [ ] Dobiti Claude API ključ, preizkusiti nekaj računov.
- [ ] Postaviti prazen repo: frontend + backend „hello world“.

### Faza 1: jedro (MVP)
- [ ] `parse_receipt.py`: slika → `{ items, total }` prek Claude API.
- [ ] `split.py` + testi.
- [ ] Zasloni: Domov → Zajem → Pregled postavk → Skupina → Dodeljevanje → Povzetek → Pošlji.
- [ ] Mock zahtevki v zaslonu *Zahtevki*.

**──── MVP: s tem lahko naredimo demo ────**

### Faza 2: kakovost
- [ ] Deljenje z deleži (npr. 2:1).
- [ ] Polish UI (animacije, Flik videz).

### Faza 3: wow
- [ ] Pogled prejemnika z razčlenitvijo.
- [ ] Ena ideja iz poglavja 7.

### Faza 4: pitch
- [ ] Diapozitivi (glej 9).
- [ ] Vaja demota vsaj 3-krat, s štoparico.

---

## 9. Pitch in demo (5 min)

| Čas | Vsebina |
|---|---|
| 0:00–0:45 | **Problem:** zgodba („6 prijateljev, račun 87,40 €, 15 minut kalkulatorja“) + številke iz intervjujev |
| 0:45–1:15 | **Rešitev** v enem stavku + zakaj v Fliku (že ga uporabljajo, plačilo je takoj) |
| 1:15–3:30 | **Demo v živo:** slikamo pravi račun → postavke → dodamo 3 ljudi → poklikamo (vključno s skupno pico) → pošljemo → na drugem telefonu prispe zahtevek |
| 3:30–4:15 | **Tehnika in varnost:** arhitektura, branje računa s Claude API, deljenje v centih, zasebnost |
| 4:15–5:00 | **Vrednost in naprej:** prihranjen čas, pravičnost, manj gotovine; naslednji koraki (deljenje v živo, integracija v pravi Flik) |

**Rezervni scenarij:** če API ali Wi-Fi odpove, ima aplikacija vgrajen „demo račun“ z vnaprej shranjenim rezultatom, ter posnetek zaslona celotnega toka.

---

## 10. Razdelitev dela (predlog za 4 osebe)

| Oseba | Naloga |
|---|---|
| A | Branje računov prek Claude API, poziv, testiranje na računih |
| B | Backend (FastAPI), `split.py` + testi, mock Flik zahtevki |
| C | Frontend: Flik videz, zasloni, kamera |
| D | Raziskava uporabnikov, pitch, diapozitivi, testiranje UX |

Prilagodite glede na število ljudi v ekipi in na to, kdo kaj zna.

---

## 11. Odprta vprašanja za ekipo
- Koliko časa traja hackathon in koliko nas je?
- Kdo priskrbi Claude API ključ (strošek je majhen)?
- Demo na pravem telefonu (deploy + HTTPS za kamero) ali na računalniku z nalaganjem slike?
- Ali predstavljamo kot „NLB Flik“ ali nevtralno kot „Flik“?
