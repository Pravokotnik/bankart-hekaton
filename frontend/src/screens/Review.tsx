import { useState } from 'react'
import { Icon, TopBar } from '../components/ui'
import { formatEur, parseEur, type Line } from '../money'

type Draft = Line & { priceText: string }

const toDraft = (l: Line): Draft => ({ ...l, priceText: (l.price_cents / 100).toFixed(2).replace('.', ',') })

export function Review({
  lines,
  totalCents,
  onBack,
  onNext,
}: {
  lines: Line[]
  totalCents: number
  onBack: () => void
  onNext: (lines: Line[]) => void
}) {
  const [drafts, setDrafts] = useState<Draft[]>(() => lines.map(toDraft))
  const [nextId, setNextId] = useState(1)

  const update = (i: number, patch: Partial<Draft>) =>
    setDrafts((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)))

  const invalid = drafts.some((d) => parseEur(d.priceText) === null || !d.name.trim() || d.quantity < 1)
  const sum = drafts.reduce((s, d) => s + (parseEur(d.priceText) ?? 0), 0)
  const diff = sum - totalCents

  return (
    <>
      <div className="screen">
        <TopBar title="Preveri postavke" onBack={onBack} subtitle="Popravi, če je kaj prebrano narobe." />
        <div className="edit-head"><span>Izdelek</span><span>Kos</span><span>Znesek</span><span /></div>
        <div className="list">
          {drafts.map((d, i) => (
            <div className="edit-row" key={d.group_id}>
              <input value={d.name} aria-label="Ime izdelka" onChange={(e) => update(i, { name: e.target.value })} />
              <input
                className="num qty"
                inputMode="numeric"
                aria-label="Število kosov"
                value={d.quantity}
                onChange={(e) => update(i, { quantity: Math.max(1, parseInt(e.target.value) || 1) })}
              />
              <input
                className="num"
                inputMode="decimal"
                aria-label="Znesek vrstice"
                value={d.priceText}
                style={parseEur(d.priceText) === null ? { color: 'var(--red)' } : undefined}
                onChange={(e) => update(i, { priceText: e.target.value })}
              />
              <button className="icon-btn" aria-label="Izbriši postavko" onClick={() => setDrafts((ds) => ds.filter((_, j) => j !== i))}>
                <Icon name="trash" size={18} />
              </button>
            </div>
          ))}
        </div>
        <button
          className="link"
          style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 6 }}
          onClick={() => {
            setDrafts((ds) => [...ds, { group_id: `n${nextId}`, name: 'Nova postavka', quantity: 1, price_cents: 0, priceText: '0,00' }])
            setNextId((n) => n + 1)
          }}
        >
          <Icon name="plus" size={18} /> Dodaj postavko
        </button>
        <div className="totals">
          <div><span>Vsota postavk</span><span className="amount">{formatEur(sum)}</span></div>
          <div><span>Skupaj na računu</span><span className="amount">{formatEur(totalCents)}</span></div>
          {diff === 0 ? (
            <div className="ok"><span>Vsota se ujema</span><Icon name="check" size={18} /></div>
          ) : (
            <div className="bad"><span>Razlika {formatEur(diff)}. Preveri postavke.</span></div>
          )}
        </div>
      </div>
      <div className="footer">
        <button
          className="btn"
          disabled={invalid || drafts.length === 0}
          onClick={() => onNext(drafts.map(({ priceText, ...l }) => ({ ...l, price_cents: parseEur(priceText)! })))}
        >
          Naprej
        </button>
      </div>
    </>
  )
}
