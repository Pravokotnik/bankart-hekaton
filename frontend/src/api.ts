export type Contact = { id: string; name: string; phone: string; color: string }

/** En kos postavke. Kosi iste vrstice na računu imajo skupen group_id. */
export type Piece = { id: string; group_id: string; name: string; price_cents: number }

export type Receipt = {
  source: 'claude' | 'demo'
  items: Piece[]
  total_cents: number
  items_sum_cents: number
}

/** piece_id -> { participant_id: delež } */
export type Assignments = Record<string, Record<string, number>>

export type Part = { item_id: string; name: string; cents: number; of: number }

export type PersonSummary = {
  participant: Contact
  amount_cents: number
  items: Part[]
  is_payer: boolean
}

export type Summary = { people: PersonSummary[]; total_cents: number }

export type FlikRequest = {
  id: string
  to: Contact
  from: Contact
  merchant: string
  amount_cents: number
  items: Part[]
  status: 'čaka' | 'plačano'
  created_at: string
}

export type BillPayload = {
  merchant: string
  items: Piece[]
  participants: string[]
  assignments: Assignments
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new Error('Strežnik ni dosegljiv. Ali backend teče na portu 8000?')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Napaka strežnika (${res.status}).`
    throw new Error(detail)
  }
  return res.json()
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  status: () => call<{ api_key: boolean }>('/api/status'),
  contacts: () => call<Contact[]>('/api/contacts'),
  parseReceipt: (file: File) => {
    const form = new FormData()
    form.append('image', file)
    return call<Receipt>('/api/receipts/parse', { method: 'POST', body: form })
  },
  demoReceipt: () => call<Receipt>('/api/receipts/demo'),
  summary: (bill: BillPayload) => call<Summary>('/api/bills/summary', json(bill)),
  send: (bill: BillPayload) =>
    call<{ requests: FlikRequest[]; summary: Summary }>('/api/bills/send', json(bill)),
  requests: () => call<FlikRequest[]>('/api/requests'),
  pay: (id: string) => call<FlikRequest>(`/api/requests/${id}/pay`, { method: 'POST' }),
}

export const PAYER = 'jaz'
