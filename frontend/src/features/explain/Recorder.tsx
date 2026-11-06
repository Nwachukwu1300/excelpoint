import { useEffect, useRef, useState } from 'react'
import { Icon } from '../../ui/Icon'
import { Button } from '../../ui/primitives'

const MAX_SECONDS = 180
const TARGET_SECONDS = 30
const MIN_SECONDS = 3
const SILENT_LEVEL = 0.02 // the loudest moment stayed below this: nothing was said, or the mic is muted

export type Take = { clip: Blob; seconds: number }
type Problem = 'denied' | 'no-mic' | 'unsupported' | 'failed' | 'short' | 'silent'

const PROBLEMS: Record<Problem, { title: string; text: string }> = {
  denied: {
    title: 'XP can’t use your microphone',
    text: 'To turn it on, select the lock or settings icon next to the web address, set Microphone to Allow, then reload the page. Or type your explanation instead.',
  },
  'no-mic': { title: 'No microphone found', text: 'Plug in a microphone or headset and try again, or type your explanation instead.' },
  unsupported: { title: 'This browser can’t record', text: 'Try the latest Chrome, Safari, Edge or Firefox, or type your explanation instead.' },
  failed: { title: 'The recording didn’t start', text: 'Try again. If it keeps happening, type your explanation instead.' },
  short: { title: 'That was too short', text: 'XP needs a few seconds to work with. Aim for 30 seconds to 3 minutes.' },
  silent: { title: 'XP couldn’t hear anything', text: 'Check your microphone isn’t muted, move a little closer and try again.' },
}

const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

function pickType() {
  for (const type of ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus']) {
    if (MediaRecorder.isTypeSupported?.(type)) return type
  }
  return ''
}

/** Record an explanation: tap to start, tap to stop (or it stops at 3 minutes). XP only listens after you stop. */
export function Recorder({ onTake, onType, prompt }: { onTake: (take: Take) => void; onType: () => void; prompt: string }) {
  const [state, setState] = useState<'idle' | 'starting' | 'recording'>('idle')
  const [seconds, setSeconds] = useState(0)
  const [problem, setProblem] = useState<Problem | null>(null)
  const stopRef = useRef<() => void>(() => {})
  const finishRef = useRef<() => void>(() => {})
  useEffect(() => () => stopRef.current(), []) // leaving the page stops the mic

  async function start() {
    setProblem(null)
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') return setProblem('unsupported')
    setState('starting')
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      setState('idle')
      const name = (e as DOMException).name
      return setProblem(name === 'NotAllowedError' || name === 'SecurityError' ? 'denied' : name === 'NotFoundError' ? 'no-mic' : 'failed')
    }
    const type = pickType()
    const recorder = new MediaRecorder(stream, { ...(type ? { mimeType: type } : {}), audioBitsPerSecond: 24000 })
    const parts: Blob[] = []
    let loudest = 0
    let context: AudioContext | null = null
    let analyser: AnalyserNode | null = null
    try {
      context = new AudioContext()
      analyser = context.createAnalyser()
      context.createMediaStreamSource(stream).connect(analyser)
    } catch { /* no level check: the server still rejects a take with no words */ }
    const samples = new Float32Array(analyser?.fftSize ?? 0)
    const began = Date.now()
    const tick = setInterval(() => {
      const elapsed = (Date.now() - began) / 1000
      setSeconds(elapsed)
      if (analyser) {
        analyser.getFloatTimeDomainData(samples)
        loudest = Math.max(loudest, Math.sqrt(samples.reduce((sum, v) => sum + v * v, 0) / samples.length))
      }
      if (elapsed >= MAX_SECONDS) stop()
    }, 200)

    function release() {
      clearInterval(tick)
      stream.getTracks().forEach(t => t.stop())
      context?.close().catch(() => {})
      stopRef.current = () => {}
    }
    function stop() {
      if (recorder.state !== 'inactive') recorder.stop()
    }
    recorder.ondataavailable = e => { if (e.data.size) parts.push(e.data) }
    recorder.onstop = () => {
      const elapsed = (Date.now() - began) / 1000
      release()
      setState('idle')
      setSeconds(0)
      if (elapsed < MIN_SECONDS) return setProblem('short')
      if (analyser && loudest < SILENT_LEVEL) return setProblem('silent')
      onTake({ clip: new Blob(parts, { type: recorder.mimeType || type || 'audio/webm' }), seconds: elapsed })
    }
    stopRef.current = () => { recorder.onstop = null; stop(); release() } // leaving the page: no take
    finishRef.current = stop
    recorder.start(1000)
    setState('recording')
  }

  const recording = state === 'recording'
  const help = problem ? PROBLEMS[problem] : null

  return (
    <div className="recorder">
      {help ? (
        <div className={`recorder-problem ${problem === 'denied' ? 'is-blocking' : ''}`} role="alert">
          <strong>{help.title}</strong>
          <p>{help.text}</p>
        </div>
      ) : (
        <p className="recorder-prompt" aria-live="polite">{recording ? 'Listening. Tap stop when you’ve finished.' : prompt}</p>
      )}
      <button
        type="button"
        className={`record-button ${recording ? 'is-recording' : ''}`}
        aria-label={recording ? 'Stop recording' : 'Start recording'}
        disabled={state === 'starting'}
        onClick={() => (recording ? finishRef.current() : start())}
      >
        <Icon name={recording ? 'stop' : 'mic'} size={28} />
      </button>
      <div className="recorder-meta">
        {recording ? (
          <>
            <span className="recorder-time" role="timer">{clock(seconds)}</span>
            <div className="recorder-track" aria-hidden="true">
              <span style={{ width: `${Math.min(100, (seconds / MAX_SECONDS) * 100)}%` }} />
              <i style={{ left: `${(TARGET_SECONDS / MAX_SECONDS) * 100}%` }} />
            </div>
            <span className="recorder-hint">{seconds < TARGET_SECONDS ? 'Aim for at least 30 seconds' : 'Stop whenever you’re done · up to 3:00'}</span>
          </>
        ) : (
          <Button variant="ghost" onClick={onType}>Type instead</Button>
        )}
      </div>
    </div>
  )
}
