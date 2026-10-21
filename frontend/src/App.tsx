import { useEffect, useMemo, useState } from 'react'
import { api, type Assignments, type BillPayload, type Contact, type FlikRequest } from './api'
import { BottomNav, StatusBar, TopBar, type Tab } from './components/ui'
import { toLines, toPieces, type Line } from './money'
import { Assign } from './screens/Assign'
import { Group } from './screens/Group'
import { Home, RECENT, TransactionList } from './screens/Home'
import { Receiver, Requests } from './screens/Requests'
import { Review } from './screens/Review'
import { Scan } from './screens/Scan'
import { Sent, Summary } from './screens/Summary'

type Step = 'scan' | 'review' | 'group' | 'assign' | 'summary' | 'sent'

const isReceiver = new URLSearchParams(window.location.search).get('view') === 'prejemnik'

export default function App() {
  const [tab, setTab] = useState<Tab>('home')
  const [step, setStep] = useState<Step | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [lines, setLines] = useState<Line[]>([])
  const [totalCents, setTotalCents] = useState(0)
  const [participants, setParticipants] = useState<string[]>([])
  const [assignments, setAssignments] = useState<Assignments>({})
  const [sent, setSent] = useState<FlikRequest[]>([])

  useEffect(() => {
    api.contacts().then(setContacts).catch(() => setContacts([]))
  }, [])

  const pieces = useMemo(() => toPieces(lines), [lines])
  const people = participants.map((id) => contacts.find((c) => c.id === id)).filter((c): c is Contact => !!c)
  const bill: BillPayload = useMemo(
    () => ({ merchant: 'Razdeljen račun', items: pieces, participants, assignments }),
    [pieces, participants, assignments],
  )

  function startSplit() {
    setLines([])
    setParticipants([])
    setAssignments({})
    setStep('scan')
  }

  function finish(t: Tab) {
    setStep(null)
    setTab(t)
  }

  let content
  if (isReceiver) {
    content = <Receiver />
  } else if (step === 'scan') {
    content = (
      <Scan
        onBack={() => setStep(null)}
        onRead={(r) => {
          setLines(toLines(r.items))
          setTotalCents(r.total_cents)
          setStep('review')
        }}
      />
    )
  } else if (step === 'review') {
    content = (
      <Review
        lines={lines}
        totalCents={totalCents}
        onBack={() => setStep('scan')}
        onNext={(edited) => {
          setLines(edited)
          setAssignments({})
          setStep('group')
        }}
      />
    )
  } else if (step === 'group') {
    content = (
      <Group
        contacts={contacts}
        selected={participants}
        onBack={() => setStep('review')}
        onNext={(ids) => {
          // Dodelitve odstranjenih oseb zavržemo.
          setAssignments((a) =>
            Object.fromEntries(
              Object.entries(a).map(([k, v]) => [k, Object.fromEntries(Object.entries(v).filter(([id]) => ids.includes(id)))]),
            ),
          )
          setParticipants(ids)
          setStep('assign')
        }}
      />
    )
  } else if (step === 'assign') {
    content = (
      <Assign
        pieces={pieces}
        people={people}
        assignments={assignments}
        onChange={setAssignments}
        onBack={() => setStep('group')}
        onNext={() => setStep('summary')}
      />
    )
  } else if (step === 'summary') {
    content = (
      <Summary
        bill={bill}
        onBack={() => setStep('assign')}
        onSent={(r) => {
          setSent(r)
          setStep('sent')
        }}
      />
    )
  } else if (step === 'sent') {
    content = <Sent requests={sent} onDone={() => finish('requests')} />
  } else if (tab === 'home') {
    content = <Home onSplit={startSplit} onAll={() => setTab('transactions')} />
  } else if (tab === 'transactions') {
    content = (
      <div className="screen">
        <TopBar title="Transakcije" />
        <TransactionList rows={RECENT} />
      </div>
    )
  } else if (tab === 'requests') {
    content = <Requests />
  } else {
    content = (
      <div className="screen">
        <TopBar title="Nastavitve" />
        <div className="empty">Nastavitve niso del prototipa.</div>
      </div>
    )
  }

  return (
    <main className="phone">
      <StatusBar />
      {content}
      {!step && !isReceiver && <BottomNav tab={tab} onTab={setTab} />}
    </main>
  )
}
