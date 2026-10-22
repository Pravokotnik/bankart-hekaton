import { Icon } from '../components/ui'
import { formatEur } from '../money'

export const RECENT = [
  { name: 'Ana N.', cents: -320, status: 'Poslano', date: '18. oktober, 14:22' },
  { name: 'Miha K.', cents: -1071, status: 'Poslano', date: '18. oktober, 14:15' },
  { name: 'Lara H.', cents: -500, status: 'Poslano', date: '16. oktober, 12:57' },
  { name: 'Tina P.', cents: -1500, status: 'Poslano', date: '15. oktober, 21:54' },
  { name: 'Jaka Z.', cents: 530, status: 'Prejeto', date: '15. oktober, 17:50' },
]

export function TransactionList({ rows }: { rows: typeof RECENT }) {
  return (
    <div className="list tx">
      {rows.map((t, i) => (
        <div className="row" key={i}>
          <div className="row-main">
            <div className="row-name">{t.name}</div>
            <span className="pill">{t.status}</span>
          </div>
          <div className="row-end">
            <div className={`amount ${t.cents < 0 ? 'out' : 'in'}`}>
              {t.cents > 0 ? '+' : ''}
              {formatEur(t.cents)}
            </div>
            <div className="row-sub">{t.date}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

export function Home({ onSplit, onAll }: { onSplit: () => void; onAll: () => void }) {
  return (
    <div className="screen home">
      <div className="home-head">
        <span className="bank">Moja banka</span>
        <button className="icon-square" aria-label="Osveži"><Icon name="refresh" size={18} /></button>
      </div>
      <div className="flik-logo">flik</div>
      <div className="actions">
        <button className="action" disabled title="Ni del prototipa">
          <span className="action-icon"><Icon name="scan" size={28} stroke={1.8} /></span>Skeniraj
        </button>
        <button className="action" disabled title="Ni del prototipa">
          <span className="action-icon"><Icon name="send" size={28} stroke={1.8} /></span>Pošlji
        </button>
        <button className="action" disabled title="Ni del prototipa">
          <span className="action-icon"><Icon name="request" size={28} stroke={1.8} /></span>Zahtevaj
        </button>
      </div>
      <button className="split-cta" onClick={onSplit}>
        <span className="action-icon">
          <Icon name="receipt" size={24} stroke={1.8} />
        </span>
        <div>
          <strong>Razdeli račun</strong>
          <span>Slikaj račun, vsak plača svoj del.</span>
        </div>
      </button>
      <div className="tx-head">
        <div className="section-label">ZADNJE TRANSAKCIJE</div>
        <button className="link" onClick={onAll}>Prikaži vse</button>
      </div>
      <TransactionList rows={RECENT} />
    </div>
  )
}
