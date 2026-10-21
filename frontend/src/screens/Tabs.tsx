import { useState } from 'react'
import { Icon, TopBar } from '../components/ui'
import { RECENT, TransactionList } from './Home'

export function Transactions() {
  const [view, setView] = useState<'history' | 'recurring'>('history')
  const [query, setQuery] = useState('')
  const rows = RECENT.filter((t) => t.name.toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="screen">
      <TopBar title="Transakcije" />
      <div className="segmented" role="tablist">
        <button role="tab" aria-selected={view === 'history'} className={view === 'history' ? 'on' : ''} onClick={() => setView('history')}>Zgodovina</button>
        <button role="tab" aria-selected={view === 'recurring'} className={view === 'recurring' ? 'on' : ''} onClick={() => setView('recurring')}>Ponavljajoče</button>
      </div>
      <label className="search">
        <Icon name="search" size={20} />
        <input placeholder="Iskanje …" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {view === 'history' ? (
        rows.length > 0 ? <TransactionList rows={rows} /> : <p className="hint">Ni zadetkov.</p>
      ) : (
        <div className="empty">Nimate ponavljajočih plačil.</div>
      )}
    </div>
  )
}

type Setting = { label: string; icon: Parameters<typeof Icon>[0]['name']; color: string; toggle?: boolean }

const ACCOUNT: Setting[] = [
  { label: 'Moj račun', icon: 'user', color: '#7f8cff' },
  { label: 'Privzeto plačilno sredstvo', icon: 'card', color: '#6cdc7a' },
  { label: 'Varnost', icon: 'lock', color: '#f2c94b' },
]

const APP: Setting[] = [
  { label: 'Potisna obvestila', icon: 'bell', color: '#ff7a66', toggle: true },
  { label: 'Zvok ob plačilu', icon: 'sound', color: '#b78cff', toggle: true },
  { label: 'Temni način', icon: 'moon', color: '#c6cbe0', toggle: true },
  { label: 'Jezik', icon: 'globe', color: '#7f8cff' },
  { label: 'Informacije', icon: 'info', color: '#6cdc7a' },
  { label: 'Novice', icon: 'news', color: '#f2c94b' },
]

function SettingList({ items, on, onToggle }: { items: Setting[]; on: Set<string>; onToggle: (l: string) => void }) {
  return (
    <div className="list">
      {items.map((s) => (
        <div className="row" key={s.label}>
          <span className="set-icon" style={{ color: s.color }}><Icon name={s.icon} size={20} /></span>
          <div className="row-main"><div className="row-name" style={{ fontWeight: 500 }}>{s.label}</div></div>
          {s.toggle ? (
            <button
              className={`toggle${on.has(s.label) ? ' on' : ''}`}
              role="switch"
              aria-checked={on.has(s.label)}
              aria-label={s.label}
              onClick={() => onToggle(s.label)}
            />
          ) : (
            <span style={{ color: 'var(--muted)' }}><Icon name="chevron" size={20} /></span>
          )}
        </div>
      ))}
    </div>
  )
}

export function Settings() {
  const [on, setOn] = useState(() => new Set(['Potisna obvestila', 'Temni način']))
  const toggle = (label: string) =>
    setOn((s) => {
      const next = new Set(s)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      return next
    })
  return (
    <div className="screen">
      <TopBar title="Nastavitve" />
      <div className="section-label">UPORABNIŠKI RAČUN</div>
      <SettingList items={ACCOUNT} on={on} onToggle={toggle} />
      <div className="section-label">APLIKACIJA</div>
      <SettingList items={APP} on={on} onToggle={toggle} />
      <button className="logout"><Icon name="logout" size={20} />Odjava</button>
    </div>
  )
}
