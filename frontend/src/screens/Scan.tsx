import { useEffect, useRef, useState } from 'react'
import { api, type Receipt } from '../api'
import { Icon, TopBar } from '../components/ui'

export function Scan({ onBack, onRead }: { onBack: () => void; onRead: (r: Receipt) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [over, setOver] = useState(false)
  const [hasKey, setHasKey] = useState<boolean | null>(null)

  useEffect(() => {
    api.status().then((s) => setHasKey(s.api_key)).catch(() => setHasKey(null))
  }, [])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  async function read(file: File) {
    setError(null)
    setPreview(URL.createObjectURL(file))
    setBusy(true)
    try {
      onRead(await api.parseReceipt(file))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function demo() {
    setError(null)
    setPreview('/demo-racun.jpg')
    setBusy(true)
    try {
      onRead(await api.demoReceipt())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="screen">
        <TopBar title="Razdeli račun" onBack={onBack} subtitle="Naloži sliko računa. Postavke in cene preberemo samodejno." />
        {preview ? (
          <img className="preview" src={preview} alt="Naložen račun" />
        ) : (
          <div
            className={`drop${over ? ' over' : ''}`}
            role="button"
            tabIndex={0}
            onClick={() => input.current?.click()}
            onKeyDown={(e) => e.key === 'Enter' && input.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setOver(true) }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setOver(false)
              const file = e.dataTransfer.files[0]
              if (file) read(file)
            }}
          >
            <Icon name="upload" size={34} />
            <strong>Naloži sliko računa</strong>
            <span>Klikni ali povleci sliko sem (JPG, PNG, WEBP)</span>
          </div>
        )}
        <input
          ref={input}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) read(file)
            e.target.value = ''
          }}
        />
        {busy && (
          <div className="reading"><span className="spinner" />Berem račun …</div>
        )}
        {error && <div className="error">{error}</div>}
        {hasKey === false && !busy && (
          <p className="hint">Branje računov ni na voljo, ker strežnik nima API ključa. Uporabi demo račun.</p>
        )}
      </div>
      <div className="footer">
        {preview && !busy && (
          <button className="btn ghost" onClick={() => { setPreview(null); setError(null) }}>Izberi drugo sliko</button>
        )}
        <button className="btn ghost" onClick={demo} disabled={busy}>Uporabi demo račun</button>
      </div>
    </>
  )
}
