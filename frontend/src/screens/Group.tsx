import { Fragment, useState } from 'react'
import { api, PAYER, type Contact } from '../api'
import { Avatar, Icon, TopBar } from '../components/ui'

function people(n: number) {
  if (n === 2) return '2 osebi'
  if (n === 3 || n === 4) return `${n} osebe`
  return `${n} oseb`
}

/** Kontakte razvrsti po prvi črki, kot imenik v Fliku. */
function letters(contacts: Contact[]): [string, Contact[]][] {
  const groups = new Map<string, Contact[]>()
  for (const c of [...contacts].sort((a, b) => a.name.localeCompare(b.name, 'sl'))) {
    const letter = c.name[0].toUpperCase()
    groups.set(letter, [...(groups.get(letter) ?? []), c])
  }
  return [...groups.entries()]
}

export function Group({
  contacts,
  selected,
  onBack,
  onAddContact,
  onNext,
}: {
  contacts: Contact[]
  selected: string[]
  onBack: () => void
  onAddContact: (c: Contact) => void
  onNext: (ids: string[]) => void
}) {
  const [chosen, setChosen] = useState<Set<string>>(() => new Set(selected.filter((id) => id !== PAYER)))
  const [query, setQuery] = useState('')
  const others = contacts.filter((c) => c.id !== PAYER)
  // Številka se ujema ne glede na zapis (031 …, +386 31 …).
  const localDigits = (t: string) => t.replace(/\D/g, '').replace(/^(00)?386|^0/, '')
  const shown = others.filter((c) =>
    c.name.toLowerCase().includes(query.toLowerCase()) ||
    (localDigits(query).length >= 3 && localDigits(c.phone).includes(localDigits(query))))

  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  // Iskalni niz, ki je videti kot telefonska številka in je ni v imeniku.
  const digits = query.replace(/[^\d+]/g, '')
  const looksLikePhone = /^\+?\d{8,15}$/.test(digits) && /^[\d+\s\-/()]+$/.test(query.trim())
  const known = others.some((c) => localDigits(c.phone) === localDigits(query))
  const offerPhone = looksLikePhone && !known

  async function addPhone() {
    setAdding(true)
    setAddError(null)
    try {
      const contact = await api.addContact(query)
      onAddContact(contact)
      setChosen((s) => new Set(s).add(contact.id))
      setQuery('')
    } catch (e) {
      setAddError((e as Error).message)
    } finally {
      setAdding(false)
    }
  }

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
        <TopBar title="Kdo je bil zraven?" onBack={onBack} subtitle="Izberi kontakte. Ti si vedno v skupini." />
        <label className="search">
          <Icon name="search" size={20} />
          <input placeholder="Poišči kontakt ali vpiši številko …" inputMode="search" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        {offerPhone ? (
          <button className="row list add-phone" onClick={addPhone} disabled={adding}>
            <span className="set-icon" style={{ color: 'var(--green-bright)' }}><Icon name="phone" size={20} /></span>
            <div className="row-main">
              <div className="row-name">Dodaj številko {query.trim()}</div>
              <div className="row-sub">Osebe ni v imeniku. Zahtevek dobi prek Flika na to številko.</div>
            </div>
            <Icon name="plus" size={20} />
          </button>
        ) : (
          query === '' && <p className="hint" style={{ margin: '-6px 0 0', textAlign: 'left' }}>Izberi iz imenika ali vpiši telefonsko številko.</p>
        )}
        {addError && <div className="error">{addError}</div>}
        {shown.length === 0 && !offerPhone && <p className="hint">Ni zadetkov. Vpiši celo telefonsko številko, da osebo dodaš.</p>}
        {letters(shown).map(([letter, group]) => (
          <Fragment key={letter}>
            <div className="letter">{letter}</div>
            <div className="list">
              {group.map((c) => (
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
            </div>
          </Fragment>
        ))}
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
