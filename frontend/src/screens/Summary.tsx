import { useEffect, useState } from 'react'
import { api, type BillPayload, type FlikRequest, type PersonSummary, type Summary as SummaryData } from '../api'
import { Avatar, Icon, TopBar } from '../components/ui'
import { formatEur } from '../money'

export function PartList({ items }: { items: PersonSummary['items'] }) {
  return (
    <div className="card-items">
      {items.map((part, i) => (
        <div key={`${part.item_id}-${i}`}>
          <span>{part.name}{part.of > 1 && <em> (deljeno na {part.of})</em>}</span>
          <span>{formatEur(part.cents)}</span>
        </div>
      ))}
    </div>
  )
}

export function Summary({
  bill,
  onBack,
  onSent,
}: {
  bill: BillPayload
  onBack: () => void
  onSent: (requests: FlikRequest[]) => void
}) {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  useEffect(() => {
    api.summary(bill).then(setSummary).catch((e: Error) => setError(e.message))
  }, [bill])

  const toSend = summary?.people.filter((p) => !p.is_payer && p.amount_cents > 0) ?? []

  async function send() {
    setSending(true)
    setError(null)
    try {
      onSent((await api.send(bill)).requests)
    } catch (e) {
      setError((e as Error).message)
      setSending(false)
    }
  }

  return (
    <>
      <div className="screen">
        <TopBar title="Povzetek" onBack={onBack} subtitle={summary ? `Skupaj ${formatEur(summary.total_cents)}` : undefined} />
        {error && <div className="error">{error}</div>}
        {!summary && !error && <div className="reading"><span className="spinner" />Računam …</div>}
        {summary?.people.map((p) => (
          <div className="card" key={p.participant.id}>
            <div className="card-head">
              <Avatar contact={p.participant} />
              <div className="row-main">
                <div className="row-name">{p.is_payer ? 'Tvoj delež' : p.participant.name}</div>
                <div className="row-sub">{p.is_payer ? 'Plačal si račun, zate ni zahtevka.' : p.participant.phone}</div>
              </div>
              <div className={`amount${p.is_payer ? '' : ' in'}`}>{formatEur(p.amount_cents)}</div>
            </div>
            <PartList items={p.items} />
          </div>
        ))}
      </div>
      <div className="footer">
        <button className="btn" disabled={!summary || sending || toSend.length === 0} onClick={send}>
          {sending ? 'Pošiljam …' : (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Icon name="send" size={20} /> Pošlji zahtevke ({toSend.length})
            </span>
          )}
        </button>
      </div>
    </>
  )
}

export function Sent({ requests, onDone }: { requests: FlikRequest[]; onDone: () => void }) {
  const total = requests.reduce((s, r) => s + r.amount_cents, 0)
  return (
    <>
      <div className="screen">
        <div className="done">
          <div className="done-mark"><Icon name="check" size={44} stroke={3} /></div>
          <h1 className="title">Zahtevki poslani</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            Skupaj zahtevaš {formatEur(total)}. Vsak prejemnik vidi tudi, kaj je imel.
          </p>
        </div>
        <div className="list">
          {requests.map((r) => (
            <div className="row" key={r.id}>
              <Avatar contact={r.to} />
              <div className="row-main"><div className="row-name">{r.to.name}</div></div>
              <div className="amount in">{formatEur(r.amount_cents)}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="footer">
        <button className="btn" onClick={onDone}>Na zahtevke</button>
      </div>
    </>
  )
}
