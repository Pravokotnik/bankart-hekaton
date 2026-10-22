import { useState } from 'react'
import { Icon, TopBar } from '../components/ui'
import { discounted, formatEur, parseEur, type Line } from '../money'

// Besedilo polj hranimo posebej, da lahko številko izbrišeš in vtipkaš novo (prazno polje je dovoljeno med tipkanjem).
type Draft = Line & { priceText: string; qtyText: string }

const toDraft = (l: Line): Draft => ({ ...l, priceText: (l.price_cents / 100).toFixed(2).replace('.', ','), qtyText: String(l.quantity) })

const validQty = (text: string) => /^\d{1,3}$/.test(text) && parseInt(text) >= 1

const PRESETS = [5, 10, 15, 20]

/** "10", "10 %", "12,5" → 10, 12.5; null, če ni veljaven odstotek. */
function parsePct(text: string): number | null {
  const n = parseFloat(text.replace('%', '').replace(',', '.').trim())
  return Number.isFinite(n) && n >= 0 && n <= 100 ? n : null
}

const pctLabel = (pct: number) => `${String(pct).replace('.', ',')} %`

export function Review({
  lines,
  totalCents,
  onBack,
  onNext,
}: {
  lines: Line[]
  /** Znesek "Skupaj" z računa; null pri ročnem vnosu. */
  totalCents: number | null
  onBack: () => void
  onNext: (lines: Line[]) => void
}) {
  const manual = totalCents === null
  const [drafts, setDrafts] = useState<Draft[]>(() =>
    lines.length > 0 ? lines.map(toDraft) : [{ group_id: 'n0', name: '', quantity: 1, price_cents: 0, priceText: '', qtyText: '1' }],
  )
  const [nextId, setNextId] = useState(1)
  // Vrstica, pri kateri je odprt vnos popusta.
  const [editingPct, setEditingPct] = useState<string | null>(null)
  const [customAll, setCustomAll] = useState('')

  const update = (i: number, patch: Partial<Draft>) =>
    setDrafts((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)))

  const asLine = (d: Draft): Line => ({ ...d, price_cents: parseEur(d.priceText) ?? 0 })
  const invalid = drafts.some((d) => parseEur(d.priceText) === null || !d.name.trim() || !validQty(d.qtyText))
  const sum = drafts.reduce((s, d) => s + (parseEur(d.priceText) ?? 0), 0)
  const afterDiscount = drafts.reduce((s, d) => s + discounted(asLine(d)), 0)
  const savings = sum - afterDiscount
  // Ujemanje z računom: cene na računu (pred popustom) ali že znižan "Skupaj" (npr. Spar plus popust).
  const diff = manual ? 0 : sum - totalCents
  const matchesAfterDiscount = !manual && savings > 0 && afterDiscount === totalCents

  // Popust na vse: enak odstotek na vseh vrsticah.
  const allPct = drafts.every((d) => (d.discount_pct ?? 0) === (drafts[0]?.discount_pct ?? 0)) ? (drafts[0]?.discount_pct ?? 0) : null
  const setAll = (pct: number) => setDrafts((ds) => ds.map((d) => ({ ...d, discount_pct: pct })))

  return (
    <>
      <div className="screen">
        <TopBar
          title={manual ? 'Vnesi postavke' : 'Preveri postavke'}
          onBack={onBack}
          subtitle={manual ? 'Za vsak izdelek vpiši ime, število kosov in skupni znesek.' : 'Popravi, če je kaj prebrano narobe.'}
        />
        <div className="card">
          <div className="big-label">CELOTEN ZNESEK{savings > 0 ? ' PO POPUSTU' : ''}</div>
          <div className="big-amount">{formatEur(savings > 0 || manual ? afterDiscount : totalCents)}</div>
          {savings > 0 && <div className="row-sub">Prihranek {formatEur(savings)} (brez popusta {formatEur(sum)})</div>}
        </div>
        <div className="edit-head"><span>Izdelek</span><span>Kos</span><span>Znesek</span><span /><span /></div>
        <div className="list">
          {drafts.map((d, i) => {
            const pct = d.discount_pct ?? 0
            const open = editingPct === d.group_id
            return (
              <div key={d.group_id} className="edit-item">
                <div className="edit-row">
                  <input value={d.name} placeholder="Ime izdelka" aria-label="Ime izdelka" onChange={(e) => update(i, { name: e.target.value })} />
                  <input
                    className="num qty"
                    inputMode="numeric"
                    aria-label="Število kosov"
                    value={d.qtyText}
                    style={d.qtyText && !validQty(d.qtyText) ? { color: 'var(--red)' } : undefined}
                    onChange={(e) => {
                      const text = e.target.value.replace(/\D/g, '').slice(0, 3)
                      update(i, validQty(text) ? { qtyText: text, quantity: parseInt(text) } : { qtyText: text })
                    }}
                    // Prazno polje ob odhodu vrne na 1.
                    onBlur={() => { if (!validQty(d.qtyText)) update(i, { qtyText: '1', quantity: 1 }) }}
                  />
                  <input
                    className="num"
                    inputMode="decimal"
                    aria-label="Znesek vrstice"
                    value={d.priceText}
                    placeholder="0,00"
                    style={d.priceText && parseEur(d.priceText) === null ? { color: 'var(--red)' } : undefined}
                    onChange={(e) => update(i, { priceText: e.target.value })}
                  />
                  <button
                    className={`icon-btn pct-btn${pct > 0 ? ' on' : ''}`}
                    aria-label={`Popust na ${d.name || 'izdelek'}`}
                    aria-expanded={open}
                    onClick={() => setEditingPct(open ? null : d.group_id)}
                  >
                    %
                  </button>
                  <button className="icon-btn" aria-label="Izbriši postavko" onClick={() => setDrafts((ds) => ds.filter((_, j) => j !== i))}>
                    <Icon name="trash" size={18} />
                  </button>
                </div>
                {(open || pct > 0) && (
                  <div className="line-discount">
                    {open ? (
                      <>
                        <span>Popust</span>
                        {PRESETS.map((p) => (
                          <button key={p} className={`chip${pct === p ? ' on' : ''}`} onClick={() => update(i, { discount_pct: p })}>{p} %</button>
                        ))}
                        <input
                          className="chip-input"
                          inputMode="decimal"
                          aria-label="Popust v odstotkih"
                          placeholder="%"
                          defaultValue={pct && !PRESETS.includes(pct) ? String(pct) : ''}
                          onChange={(e) => {
                            const v = parsePct(e.target.value)
                            if (v !== null) update(i, { discount_pct: v })
                          }}
                        />
                        {pct > 0 && <button className="chip" onClick={() => update(i, { discount_pct: 0 })}>Brez</button>}
                      </>
                    ) : (
                      <span>Popust {pctLabel(pct)}</span>
                    )}
                    {pct > 0 && <span className="line-discount-price">{formatEur(discounted(asLine(d)))}</span>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <button
          className="link"
          style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 6 }}
          onClick={() => {
            setDrafts((ds) => [...ds, { group_id: `n${nextId}`, name: '', quantity: 1, price_cents: 0, priceText: '', qtyText: '1', discount_pct: allPct ?? 0 }])
            setNextId((n) => n + 1)
          }}
        >
          <Icon name="plus" size={18} /> Dodaj postavko
        </button>

        <div className="card discount-card">
          <div className="big-label">POPUST NA CEL RAČUN</div>
          <div className="chips">
            <button className={`chip${allPct === 0 ? ' on' : ''}`} onClick={() => { setAll(0); setCustomAll('') }}>Brez</button>
            {PRESETS.map((p) => (
              <button key={p} className={`chip${allPct === p ? ' on' : ''}`} onClick={() => { setAll(p); setCustomAll('') }}>{p} %</button>
            ))}
            <input
              className="chip-input"
              inputMode="decimal"
              aria-label="Popust na cel račun v odstotkih"
              placeholder="Drugo %"
              value={customAll}
              onChange={(e) => {
                setCustomAll(e.target.value)
                const v = parsePct(e.target.value)
                if (v !== null) setAll(v)
              }}
            />
          </div>
          <p className="hint" style={{ textAlign: 'left', margin: 0 }}>
            {allPct === null ? 'Popust je nastavljen posebej po izdelkih (gumb % v vrstici).' : 'Za popust na en izdelek tapni % v njegovi vrstici.'}
          </p>
        </div>

        {!manual && (
          <div className="check-sum">
            <div className="line">
              <span>
                Seštevek postavk zgoraj
                <small>{savings > 0 ? `po popustu · pred popustom ${formatEur(sum)}` : 'kar si bomo razdelili'}</small>
              </span>
              <span className="amount">{formatEur(afterDiscount)}</span>
            </div>
            <div className="line">
              <span>Znesek „Skupaj“ na računu<small>prebrano z računa</small></span>
              <span className="amount">{formatEur(totalCents)}</span>
            </div>
            {diff === 0 || matchesAfterDiscount ? (
              <div className="verdict ok">
                <Icon name="check" size={18} stroke={3} />
                {savings > 0 && !matchesAfterDiscount
                  ? `Cene se ujemajo z računom, popust ${formatEur(savings)} je odštet.`
                  : 'Zneska se ujemata.'}
              </div>
            ) : (
              <div className="verdict bad">
                <span>
                  {savings > 0 ? `Cene pred popustom (${formatEur(sum)}) so` : 'Postavke so skupaj'} za{' '}
                  <b>{formatEur(Math.abs(diff))}</b> {diff > 0 ? 'več' : 'manj'} kot na računu.{' '}
                  {diff > 0 ? 'Preveri ceno ali izbriši odvečno postavko.' : 'Preveri ceno ali dodaj manjkajočo postavko.'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="footer">
        <button
          className="btn"
          disabled={invalid || drafts.length === 0}
          onClick={() => onNext(drafts.map(({ priceText, qtyText, ...l }) => ({ ...l, quantity: parseInt(qtyText), price_cents: parseEur(priceText)! })))}
        >
          Naprej{savings > 0 ? ` (${formatEur(afterDiscount)})` : ''}
        </button>
      </div>
    </>
  )
}
