import { useEffect, useState } from 'react'
import { api, type FlikRequest } from '../api'
import { Avatar, TopBar } from '../components/ui'
import { formatEur } from '../money'
import { PartList } from './Summary'

function useRequests() {
  const [requests, setRequests] = useState<FlikRequest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    const load = () =>
      api.requests()
        .then((r) => { if (alive) { setRequests(r); setError(null) } })
        .catch((e: Error) => alive && setError(e.message))
    load()
    // Osveževanje, da se status "plačano" iz pogleda prejemnika pokaže sam.
    const timer = setInterval(load, 2000)
    return () => { alive = false; clearInterval(timer) }
  }, [])
  return { requests, setRequests, error }
}

const time = (iso: string) => {
  const d = new Date(iso)
  return `${d.getDate()}. ${d.toLocaleString('sl-SI', { month: 'long' })}, ${d.toLocaleTimeString('sl-SI', { hour: '2-digit', minute: '2-digit' })}`
}

export function Requests() {
  const { requests, error } = useRequests()
  const [openId, setOpenId] = useState<string | null>(null)
  return (
    <div className="screen">
      <TopBar title="Zahtevki" />
      {error && <div className="error">{error}</div>}
      {requests?.length === 0 && <div className="empty">Nimate zahtevkov.</div>}
      {requests && requests.length > 0 && (
        <div className="list">
          {requests.map((r) => (
            <div key={r.id}>
              <button className="row" onClick={() => setOpenId(openId === r.id ? null : r.id)} aria-expanded={openId === r.id}>
                <Avatar contact={r.to} />
                <div className="row-main">
                  <div className="row-name">{r.to.name}</div>
                  <span className={`pill${r.status === 'čaka' ? ' wait' : ''}`}>
                    {r.status === 'čaka' ? 'Čaka na plačilo' : 'Plačano'}
                  </span>
                </div>
                <div className="row-end">
                  <div className="amount in">{formatEur(r.amount_cents)}</div>
                  <div className="row-sub">{time(r.created_at)}</div>
                </div>
              </button>
              {openId === r.id && <div style={{ padding: '0 14px 12px' }}><PartList items={r.items} /></div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Kaj vidi oseba, ki dobi zahtevek (simulacija drugega telefona). */
export function Receiver() {
  const { requests, setRequests, error } = useRequests()
  const [paying, setPaying] = useState<string | null>(null)

  async function pay(id: string) {
    setPaying(id)
    try {
      const updated = await api.pay(id)
      setRequests((rs) => rs?.map((r) => (r.id === id ? updated : r)) ?? null)
    } finally {
      setPaying(null)
    }
  }

  return (
    <div className="screen">
      <TopBar title="Prejeti zahtevki" />
      <div className="receiver-banner">Pogled prejemnika: tako zahtevek vidijo prijatelji v svoji Flik aplikaciji.</div>
      {error && <div className="error">{error}</div>}
      {requests?.length === 0 && <div className="empty">Nimate zahtevkov.</div>}
      {requests?.map((r) => (
        <div className="card" key={r.id}>
          <div className="card-head">
            <Avatar contact={r.to} />
            <div className="row-main">
              <div className="row-name">{r.to.name}</div>
              <div className="row-sub">Zahtevek za razdeljen račun</div>
            </div>
            <div className="amount out">{formatEur(r.amount_cents)}</div>
          </div>
          <PartList items={r.items} />
          <div style={{ marginTop: 12 }}>
            {r.status === 'plačano' ? (
              <span className="pill">Plačano</span>
            ) : (
              <button className="btn" onClick={() => pay(r.id)} disabled={paying === r.id}>
                {paying === r.id ? 'Plačujem …' : `Plačaj ${formatEur(r.amount_cents)}`}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
