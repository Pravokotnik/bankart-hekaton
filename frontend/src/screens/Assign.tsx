import { useMemo, useState } from 'react'
import { PAYER, type Assignments, type Contact, type Piece } from '../api'
import { Avatar, Icon, TopBar } from '../components/ui'
import { formatEur } from '../money'

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
  // Izbranih je lahko več oseb; tap na izdelek ga dodeli vsem izbranim (na enake dele).
  const [selected, setSelected] = useState<Set<string>>(() => new Set([people[1]?.id ?? PAYER]))
  const togglePerson = (id: string) =>
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
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

  const who = ids.filter((id) => selected.has(id))
  const allSelected = who.length === ids.length
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(ids))

  /** Tap na vrstico: izbranim osebam doda kose; če jih že imajo vse, jim jih odvzame. */
  function toggle(target: Piece[]) {
    if (who.length === 0) return
    const hasAll = target.every((p) => who.every((id) => assignments[p.id]?.[id]))
    const next: Assignments = { ...assignments }
    for (const p of target) {
      const current = { ...(next[p.id] ?? {}) }
      for (const id of who) {
        if (hasAll) delete current[id]
        else current[id] = 1
      }
      next[p.id] = current
    }
    onChange(next)
  }

  // "Počisti": brez izbire ali vsi izbrani → vse; sicer samo izbrane osebe (deljeni izdelki ostanejo drugim).
  const clearsEverything = who.length === 0 || allSelected
  const clearCount = clearsEverything
    ? pieces.length - unassigned.length
    : pieces.filter((p) => who.some((id) => assignments[p.id]?.[id])).length

  function clear() {
    if (clearsEverything) {
      onChange({})
      return
    }
    const next: Assignments = {}
    for (const [pieceId, shares] of Object.entries(assignments)) {
      next[pieceId] = Object.fromEntries(Object.entries(shares).filter(([id]) => !selected.has(id)))
    }
    onChange(next)
  }

  /** Vse nedodeljene izdelke dodeli izbranim osebam (na enake dele). */
  function rest() {
    if (who.length === 0) return
    const next: Assignments = { ...assignments }
    for (const p of unassigned) next[p.id] = Object.fromEntries(who.map((id) => [id, 1]))
    onChange(next)
  }

  const firstName = (id: string) => (id === PAYER ? 'Jaz' : byId[id].name.split(' ')[0])
  const names = (list: string[]) =>
    list.length <= 1 ? list.map(firstName).join('') : `${list.slice(0, -1).map(firstName).join(', ')} in ${firstName(list[list.length - 1])}`
  const activeName = allSelected ? 'vse' : who.length === 1 && who[0] === PAYER ? 'sebe' : names(who)
  const clearLabel = clearsEverything
    ? 'Počisti vse'
    : who.length > 1 ? 'Počisti izbrane' : who[0] === PAYER ? 'Počisti moje' : `Počisti: ${firstName(who[0])}`

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
        <div className="people-bar" role="group" aria-label="Izberi eno ali več oseb">
          {people.map((p) => (
            <button key={p.id} role="checkbox" aria-checked={selected.has(p.id)}
              className={`person${selected.has(p.id) ? ' active' : ''}`} onClick={() => togglePerson(p.id)}>
              <Avatar contact={p} />
              <span>{p.id === PAYER ? 'Jaz' : p.name.split(' ')[0]}</span>
              <span className="owed">{formatEur(owed[p.id])}</span>
            </button>
          ))}
          <button role="checkbox" aria-checked={allSelected}
            className={`person${allSelected ? ' active' : ''}`} onClick={toggleAll}>
            <span className="avatar" style={{ color: 'var(--text)' }}>VSI</span>
            <span>Vsi</span>
            <span className="owed">skupno</span>
          </button>
        </div>
        <div className="assign-hint-row">
          <p className="assign-hint">
            {who.length === 0
              ? 'Izberi eno ali več oseb zgoraj, nato tapni izdelke.'
              : <>Tapni izdelke za <b>{activeName}</b>.{who.length > 1 && ' Razdelijo se na enake dele.'}</>}
          </p>
          <button className="clear-btn" onClick={clear} disabled={clearCount === 0}>
            <Icon name="trash" size={15} /> {clearLabel}
          </button>
        </div>
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
            {who.length > 0 && (
              <button className="btn ghost rest-btn" onClick={rest}>
                <span>Ostalo ({unassigned.length}) dodeli:</span>
                {allSelected ? (
                  <span className="rest-who">vsem na enake dele</span>
                ) : (
                  <span className="rest-who">
                    {who.slice(0, 4).map((id) => <Avatar key={id} contact={byId[id]} small />)}
                    {who.length === 1 ? (who[0] === PAYER ? 'meni' : firstName(who[0])) : names(who)}
                  </span>
                )}
              </button>
            )}
          </>
        )}
        <button className="btn" disabled={unassigned.length > 0} onClick={onNext}>Povzetek</button>
      </div>
    </>
  )
}
