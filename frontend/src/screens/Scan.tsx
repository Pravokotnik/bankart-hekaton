import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Receipt } from '../api'
import { Icon, TopBar } from '../components/ui'

type Camera = 'starting' | 'live' | 'unavailable'

export function Scan({
  onBack,
  onRead,
  onManual,
}: {
  onBack: () => void
  onRead: (r: Receipt) => void
  onManual: () => void
}) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const mounted = useRef(true)
  const [camera, setCamera] = useState<Camera>('starting')
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [readerReady, setReaderReady] = useState<boolean | null>(null)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    api.status().then((s) => setReaderReady(s.ready)).catch(() => setReaderReady(false))
  }, [])

  // Števec med branjem: lokalni model potrebuje 10–30 s, uporabnik naj vidi, da se nekaj dogaja.
  useEffect(() => {
    if (!busy) return
    const started = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500)
    return () => {
      clearInterval(timer)
      setSeconds(0)
    }
  }, [busy])

  const stopCamera = useCallback(() => {
    stream.current?.getTracks().forEach((t) => t.stop())
    stream.current = null
  }, [])

  const startCamera = useCallback(async () => {
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1440 } },
        audio: false,
      })
      // Zaslon smo morda zapustili, preden je kamera odgovorila.
      if (!mounted.current) {
        media.getTracks().forEach((t) => t.stop())
        return
      }
      stream.current = media
      if (video.current) video.current.srcObject = media
      setCamera('live')
    } catch {
      setCamera('unavailable')
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    startCamera()
    return () => {
      mounted.current = false
      stopCamera()
    }
  }, [startCamera, stopCamera])

  useEffect(() => () => { if (preview?.startsWith('blob:')) URL.revokeObjectURL(preview) }, [preview])

  async function run(load: () => Promise<Receipt>, previewUrl: string) {
    stopCamera()
    setError(null)
    setPreview(previewUrl)
    setBusy(true)
    try {
      onRead(await load())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const readFile = (file: File) => run(() => api.parseReceipt(file), URL.createObjectURL(file))

  function capture() {
    const v = video.current
    if (!v || !v.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    canvas.getContext('2d')!.drawImage(v, 0, 0)
    canvas.toBlob((blob) => {
      if (blob) readFile(new File([blob], 'racun.jpg', { type: 'image/jpeg' }))
    }, 'image/jpeg', 0.92)
  }

  function retake() {
    setPreview(null)
    setError(null)
    setCamera('starting')
    startCamera()
  }

  return (
    <>
      <div className="screen">
        <TopBar title="Razdeli račun" onBack={onBack} subtitle="Slikaj račun. Postavke in cene preberemo samodejno." />
        <div className="viewfinder">
          {preview ? (
            <img src={preview} alt="Zajet račun" />
          ) : (
            <>
              <video ref={video} autoPlay playsInline muted style={{ opacity: camera === 'live' ? 1 : 0 }} />
              {camera === 'live' && <div className="frame-guide" aria-hidden="true" />}
              {camera === 'starting' && <div className="viewfinder-msg"><span className="spinner" />Vklapljam kamero …<br />Če brskalnik vpraša, dovoli dostop do kamere.</div>}
              {camera === 'unavailable' && (
                <div className="viewfinder-msg">
                  <Icon name="camera" size={34} />
                  Kamera ni na voljo. Naloži sliko računa ali vnesi postavke ročno.
                </div>
              )}
            </>
          )}
          {!preview && camera === 'live' && (
            <button className="shutter" onClick={capture} aria-label="Slikaj račun" />
          )}
        </div>
        {busy && (
          <div className="reading">
            <span className="spinner" />
            {seconds < 3 ? 'Berem besedilo z računa …' : `Prepoznavam postavke … ${seconds} s`}
          </div>
        )}
        {busy && seconds >= 3 && <p className="hint">Bere lokalni model, slika ne zapusti računalnika. Traja 10–30 s.</p>}
        {readerReady === false && !busy && !preview && (
          <p className="hint">Model za branje računov ne teče. Zaženi llama-server (glej README) ali uporabi demo račun.</p>
        )}
        {error && <div className="error">{error} Lahko poskusiš znova ali vneseš postavke ročno.</div>}
      </div>
      <div className="footer">
        {preview && !busy && <button className="btn ghost" onClick={retake}>Slikaj znova</button>}
        {/* Pravo polje za datoteko v oznaki: deluje tudi v brskalnikih, ki blokirajo klik iz kode. */}
        <label className={`btn ghost icon-label${busy ? ' disabled' : ''}`}>
          <input
            className="visually-hidden"
            type="file"
            accept="image/*"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) readFile(file)
              e.target.value = ''
            }}
          />
          <Icon name="upload" size={20} /> Naloži sliko računa
        </label>
        <button className="btn ghost icon-label" onClick={() => { stopCamera(); onManual() }} disabled={busy}>
          <Icon name="edit" size={20} /> Vnesi ročno
        </button>
        <button className="link" style={{ alignSelf: 'center', padding: 4 }} disabled={busy}
          onClick={() => run(api.demoReceipt, '/demo-racun.jpg')}>
          Uporabi demo račun
        </button>
      </div>
    </>
  )
}
