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
  const input = useRef<HTMLInputElement>(null)
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const mounted = useRef(true)
  const [camera, setCamera] = useState<Camera>('starting')
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
        {busy && <div className="reading"><span className="spinner" />Berem račun …</div>}
        {error && <div className="error">{error} Lahko poskusiš znova ali vneseš postavke ročno.</div>}
        <input
          ref={input}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) readFile(file)
            e.target.value = ''
          }}
        />
      </div>
      <div className="footer">
        {preview && !busy ? (
          <button className="btn ghost" onClick={retake}>Slikaj znova</button>
        ) : (
          <button className="btn ghost icon-label" onClick={() => input.current?.click()} disabled={busy}>
            <Icon name="upload" size={20} /> Naloži sliko računa
          </button>
        )}
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
