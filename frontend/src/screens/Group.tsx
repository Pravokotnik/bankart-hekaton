import { useState } from 'react'
import { PAYER, type Contact } from '../api'
import { Avatar, Icon, TopBar } from '../components/ui'

function people(n: number) {
  if (n === 2) return '2 osebi'
  if (n === 3 || n === 4) return `${n} osebe`
  return `${n} oseb`
}

export function Group({
  contacts,
  selected,
  onBack,
  onNext,
}: {
  contacts: Contact[]
  selected: string[]
  onBack: () => void
  onNext: (ids: string[]) => void
}) {
  const [chosen, setChosen] = useState<Set<string>>(() => new Set(selected.filter((id) => id !== PAYER)))
  const [query, setQuery] = useState('')
  const others = contacts.filter((c) => c.id !== PAYER)
  const shown = others.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()) || c.phone.replace(/\s/g, '').includes(query.replace(/\s/g, '')))

  const toggle = (id: string) =>
    setChosen((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <>
      <div className="screen">
        <TopBar title="Kdo je bil zraven?" onBack={onBack} subtitle="Ti si vedno v skupini." />
        <label className="search">
          <Icon name="search" size={20} />
          <input placeholder="Iskanje …" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <div className="list">
          {shown.map((c) => (
            <button className="row" key={c.id} onClick={() => toggle(c.id)} aria-pressed={chosen.has(c.id)}>
              <Avatar contact={c} />
              <div className="row-main">
                <div className="row-name">{c.name}</div>
                <div className="row-sub">{c.phone}</div>
              </div>
              <span className={`check${chosen.has(c.id) ? ' on' : ''}`}>
                {chosen.has(c.id) && <Icon name="check" size={16} stroke={3} />}
              </span>
            </button>
          ))}
          {shown.length === 0 && <div className="row"><span className="row-sub">Ni zadetkov.</span></div>}
        </div>
      </div>
      <div className="footer">
        <button
          className="btn"
          disabled={chosen.size === 0}
          onClick={() => onNext([PAYER, ...others.filter((c) => chosen.has(c.id)).map((c) => c.id)])}
        >
          {chosen.size === 0 ? 'Izberi vsaj eno osebo' : `Naprej (${people(chosen.size + 1)})`}
        </button>
      </div>
    </>
  )
}
