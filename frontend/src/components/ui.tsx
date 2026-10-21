import type { ReactNode } from 'react'
import type { Contact } from '../api'
import { initials } from '../money'

export type Tab = 'home' | 'transactions' | 'requests' | 'settings'

const ICONS: Record<string, ReactNode> = {
  back: <path d="M15 5l-7 7 7 7" />,
  swap: <path d="M4 8h14l-4-4M20 16H6l4 4" />,
  bell: <path d="M6 16V11a6 6 0 0112 0v5l1.5 2h-15L6 16zM10 20a2 2 0 004 0" />,
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5l2 2.3 3-.6.9 2.9 2.8 1.3-.9 2.9 1.6 2.6-2.4 1.8.1 3-3 .4-1.6 2.6L12 19.6l-2.5 1.4-1.6-2.6-3-.4.1-3-2.4-1.8 1.6-2.6-.9-2.9 2.8-1.3.9-2.9 3 .6z" />
    </>
  ),
  scan: <path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 9v6M10 9v6M13 9v6M16 9v6" />,
  send: <path d="M4 10v9a1 1 0 001 1h12a1 1 0 001-1v-3M14 4h6v6M20 4l-8 8M4 7h5" />,
  request: <path d="M4 5h12a1 1 0 011 1v4M4 5v14a1 1 0 001 1h12a1 1 0 001-1v-3M8 14h4M10 12v4M14 13h6" />,
  receipt: <path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3zM9 8h6M9 12h6M9 16h3" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  chevron: <path d="M9 6l6 6-6 6" />,
  trash: <path d="M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13" />,
  plus: <path d="M12 5v14M5 12h14" />,
  refresh: <path d="M20 11a8 8 0 00-14.5-4.5L4 8M4 4v4h4M4 13a8 8 0 0014.5 4.5L20 16M20 20v-4h-4" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1-4 4.5-6 8-6s7 2 8 6" />
    </>
  ),
  card: <path d="M3 6h18v12H3zM3 10h18M7 15h4" />,
  lock: <path d="M6 11h12v10H6zM8 11V8a4 4 0 018 0v3" />,
  sound: <path d="M4 9v6h4l5 4V5L8 9H4zM16 9a4 4 0 010 6M18.5 6.5a7.5 7.5 0 010 11" />,
  moon: <path d="M20 14.5A8 8 0 119.5 4a6.5 6.5 0 0010.5 10.5z" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.5" />
    </>
  ),
  news: <path d="M5 4h11v16H5zM16 8h3v10a2 2 0 01-2 2M8 8h5M8 12h5M8 16h3" />,
  logout: <path d="M14 4H5v16h9M10 12h11M17 8l4 4-4 4" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6" />
      <path d="M20 20l-4.5-4.5" />
    </>
  ),
}

export function Icon({ name, size = 22, stroke = 2 }: { name: keyof typeof ICONS; size?: number; stroke?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[name]}
    </svg>
  )
}

export function FlikMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <text x="12" y="15" textAnchor="middle" fontSize="7" fontFamily="Roboto Mono, monospace" fill="currentColor">flik</text>
    </svg>
  )
}

export function StatusBar() {
  return (
    <div className="statusbar">
      <span>19:30</span>
      <span>5G ▮▮▮ 65%</span>
    </div>
  )
}

export function TopBar({ title, onBack, subtitle }: { title: string; onBack?: () => void; subtitle?: string }) {
  return (
    <>
      {onBack && (
        <div className="topbar">
          <button className="back" onClick={onBack} aria-label="Nazaj">
            <Icon name="back" size={30} stroke={2.4} />
          </button>
        </div>
      )}
      <h1 className={`title${onBack ? ' sub' : ''}`}>{title}</h1>
      {subtitle && <p className="subtitle">{subtitle}</p>}
    </>
  )
}

const TABS: { id: Tab; label: string; icon: ReactNode }[] = [
  { id: 'home', label: 'Domov', icon: <FlikMark /> },
  { id: 'transactions', label: 'Transakcije', icon: <Icon name="swap" /> },
  { id: 'requests', label: 'Zahtevki', icon: <Icon name="bell" /> },
  { id: 'settings', label: 'Nastavitve', icon: <Icon name="gear" /> },
]

export function BottomNav({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <nav className="nav">
      {TABS.map((t) => (
        <button key={t.id} className={t.id === tab ? 'active' : ''} onClick={() => onTab(t.id)}>
          {t.icon}
          {t.label}
        </button>
      ))}
    </nav>
  )
}

export function Avatar({ contact, small }: { contact: Contact; small?: boolean }) {
  return (
    <span className={`avatar${small ? ' sm' : ''}`} style={{ color: contact.color }} title={contact.name}>
      {initials(contact.name)}
    </span>
  )
}
