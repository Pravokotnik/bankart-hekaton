import { useMemo, useState } from 'react'
import { PAYER, type Assignments, type Contact, type Piece } from '../api'
import { Avatar, Icon, TopBar } from '../components/ui'
import { formatEur } from '../money'

const ALL = '__all'

/** Enako razdeli znesek; odvečni centi gredo najprej plačniku, nato po vrsti. */
function splitEven(total: number, people: string[]): Record<string, number> {
  const order = [...people].sort((a, b) => (a === PAYER ? -1 : b === PAYER ? 1 : 0))
  const base = Math.floor(total / people.length)
  const extra = total - base * people.length
  return Object.fromEntries(order.map((p, i) => [p, base + (i < extra ? 1 : 0)]))
}

function missingText(n: number) {
  if (n === 1) return 'Še 1 izdelek ni dodeljen.'
  if (n === 2) return 'Še 2 izdelka nista dodeljena.'
  if (n === 3 || n === 4) return `Še ${n} izdelki niso dodeljeni.`
  return `Še ${n} izdelkov ni dodeljenih.`
}

const holders = (assignments: Assignments, piece: Piece) => Object.keys(assignments[piece.id] ?? {})

export function Assign({
  pieces,
  people,
  assignments,
  onChange,
  onBack,
  onNext,
}: {
  pieces: Piece[]
  people: Contact[]
  assignments: Assignments
  onChange: (a: Assignments) => void
  onBack: () => void
  onNext: () => void
}) {
  const [active, setActive] = useState<string>(people[1]?.id ?? PAYER)
  const [open, setOpen] = useState<Set<string>>(new Set())

  const groups = useMemo(() => {
    const map = new Map<string, Piece[]>()
    for (const p of pieces) map.set(p.group_id, [...(map.get(p.group_id) ?? []), p])
    return [...map.values()]
  }, [pieces])

  const ids = people.map((p) => p.id)
  const byId = Object.fromEntries(people.map((p) => [p.id, p]))

  const owed = useMemo(() => {
    const sums: Record<string, number> = Object.fromEntries(ids.map((id) => [id, 0]))
    for (const piece of pieces) {
      const who = holders(assignments, piece)
      if (who.length === 0) continue
      for (const [id, cents] of Object.entries(splitEven(piece.price_cents, who))) sums[id] += cents
    }
    return sums
  }, [pieces, assignments, ids])

  const unassigned = pieces.filter((p) => holders(assignments, p).length === 0)

  /** Tap na vrstico: aktivni osebi (ali vsem) doda ali odvzame vse podane kose. */
  function toggle(target: Piece[]) {
    const who = active === ALL ? ids : [active]
    const hasAll = target.every((p) => who.every((id) => assignments[p.id]?.[id]))
    const next: Assignments = { ...assignments }
    for (const p of target) {
      const current = { ...(next[p.id] ?? {}) }
      if (active === ALL) {
        next[p.id] = hasAll ? {} : Object.fromEntries(ids.map((id) => [id, 1]))
        continue
      }
      if (hasAll) delete current[active]
      else current[active] = 1
      next[p.id] = current
    }
    onChange(next)
  }

  function rest() {
    const next: Assignments = { ...assignments }
    for (const p of unassigned) next[p.id] = { [PAYER]: 1 }
    onChange(next)
  }

  const activeName = active === ALL ? 'vse' : active === PAYER ? 'sebe' : byId[active].name.split(' ')[0]

  function holderAvatars(target: Piece[]) {
    const who = ids.filter((id) => target.some((p) => assignments[p.id]?.[id]))
    if (who.length === 0) return <span className="tag-unassigned">Nedodeljeno</span>
    return (
      <span className="avatar-stack">
        {who.map((id) => <Avatar key={id} contact={byId[id]} small />)}
      </span>
    )
  }

  return (
    <>
      <div className="screen">
        <TopBar title="Kdo je imel kaj?" onBack={onBack} />
        <div className="people-bar" role="radiogroup" aria-label="Izberi osebo">
          {people.map((p) => (
            <button key={p.id} role="radio" aria-checked={active === p.id}
              className={`person${active === p.id ? ' active' : ''}`} onClick={() => setActive(p.id)}>
              <Avatar contact={p} />
              <span>{p.id === PAYER ? 'Jaz' : p.name.split(' ')[0]}</span>
              <span className="owed">{formatEur(owed[p.id])}</span>
            </button>
          ))}
          <button role="radio" aria-checked={active === ALL}
            className={`person${active === ALL ? ' active' : ''}`} onClick={() => setActive(ALL)}>
            <span className="avatar" style={{ color: 'var(--text)' }}>VSI</span>
            <span>Vsi</span>
            <span className="owed">skupno</span>
          </button>
        </div>
        <p className="assign-hint">
          Tapni izdelke za <b>{activeName}</b>.{active === ALL && ' Razdelijo se na enake dele.'}
        </p>
        <div className="list">
          {groups.map((group) => {
            const first = group[0]
            const total = group.reduce((s, p) => s + p.price_cents, 0)
            const multi = group.length > 1
            const isOpen = open.has(first.group_id)
            const missing = group.some((p) => holders(assignments, p).length === 0)
            return (
              <div key={first.group_id}>
                <div className={`item${missing ? ' unassigned' : ''}`}>
                  {multi && (
                    <button
                      className={`qty-toggle${isOpen ? ' open' : ''}`}
                      aria-expanded={isOpen}
                      aria-label={isOpen ? 'Strni kose' : 'Razširi na posamezne kose'}
                      onClick={() => setOpen((s) => {
                        const n = new Set(s)
                        if (n.has(first.group_id)) n.delete(first.group_id)
                        else n.add(first.group_id)
                        return n
                      })}
                    >
                      <Icon name="chevron" size={14} stroke={3} />×{group.length}
                    </button>
                  )}
                  <button className="item-body" onClick={() => toggle(group)}>
                    <div className="row-main">
                      <div className="row-name">{first.name}</div>
                      <div className="row-sub">
                        {formatEur(total)}
                        {multi && !isOpen && ` · ${group.length} × ${formatEur(first.price_cents)}`}
                      </div>
                    </div>
                    {holderAvatars(group)}
                  </button>
                </div>
                {multi && isOpen && group.map((piece, i) => (
                  <div key={piece.id} className={`item piece${holders(assignments, piece).length === 0 ? ' unassigned' : ''}`}>
                    <button className="item-body" onClick={() => toggle([piece])}>
                      <div className="row-main">
                        <div className="row-name" style={{ fontWeight: 500 }}>{piece.name} {i + 1}</div>
                        <div className="row-sub">{formatEur(piece.price_cents)}</div>
                      </div>
                      {holderAvatars([piece])}
                    </button>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>
      <div className="footer">
        {unassigned.length > 0 && (
          <>
            <div className="footer-note warn">
              {missingText(unassigned.length)}
            </div>
            <button className="btn ghost" onClick={rest}>Ostalo je moje</button>
          </>
        )}
        <button className="btn" disabled={unassigned.length > 0} onClick={onNext}>Povzetek</button>
      </div>
    </>
  )
}
