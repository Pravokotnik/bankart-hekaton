import type { Piece } from './api'

export function formatEur(cents: number): string {
  const sign = cents < 0 ? '-' : ''
  const abs = Math.abs(cents)
  const euros = Math.floor(abs / 100).toLocaleString('sl-SI')
  return `${sign}${euros},${String(abs % 100).padStart(2, '0')} €`
}

/** "8,50" ali "8.50" -> 850; null, če vnos ni veljaven znesek. */
export function parseEur(text: string): number | null {
  const normalized = text.replace(/\s|€/g, '').replace(',', '.')
  if (!/^\d+(\.\d{0,2})?$/.test(normalized)) return null
  return Math.round(parseFloat(normalized) * 100)
}

/** Vrstica na računu (en ali več enakih kosov). */
export type Line = { group_id: string; name: string; quantity: number; price_cents: number }

export function toLines(pieces: Piece[]): Line[] {
  const lines = new Map<string, Line>()
  for (const p of pieces) {
    const line = lines.get(p.group_id)
    if (line) {
      line.quantity += 1
      line.price_cents += p.price_cents
    } else {
      lines.set(p.group_id, { group_id: p.group_id, name: p.name, quantity: 1, price_cents: p.price_cents })
    }
  }
  return [...lines.values()]
}

/** Razbije vrstico na kose; odvečni centi gredo prvim kosom (enako kot backend). */
export function toPieces(lines: Line[]): Piece[] {
  return lines.flatMap((line) => {
    const qty = Math.max(1, Math.floor(line.quantity))
    const base = Math.floor(line.price_cents / qty)
    const extra = line.price_cents - base * qty
    return Array.from({ length: qty }, (_, i) => ({
      id: `${line.group_id}-${i}`,
      group_id: line.group_id,
      name: line.name,
      price_cents: base + (i < extra ? 1 : 0),
    }))
  })
}

export function initials(name: string): string {
  if (name === 'Jaz') return 'JAZ'
  // Oseba, dodana samo s telefonsko številko: zadnji dve števki.
  if (/^[+\d]/.test(name)) return name.replace(/\D/g, '').slice(-2)
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
