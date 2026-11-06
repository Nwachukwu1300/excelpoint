import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { ApiError } from '../../lib/api'
import { useOneAtATime } from '../../lib/useOneAtATime'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { Icon } from '../../ui/Icon'
import { Button, IconButton, ProgressBar, Skeleton, XpAvatar, buttonClass } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import {
  resetTime, startSession, transcribe, useDeleteSession, useOverview, useSendTurn, useSession, useFinish,
  type Limit, type NotCovered, type Turn,
} from './api'
import { MissingSoFar, Marks, SessionSummary } from './Feedback'
import { Recorder, type Take } from './Recorder'
import { readMuted, saveMuted, speak, stopSpeaking } from './voice'
import '../../styles/chat.css'
import '../../styles/quiz.css'
import '../../styles/subjects.css'
import '../../styles/explain.css'

const MAX = 4000

/** /subjects/:id/explain picks a topic; /subjects/:id/explain/:sessionId is the session itself. */
export function ExplainPage() {
  const params = useParams()
  const subjectId = Number(params.subjectId)
  const sessionId = params.sessionId ? Number(params.sessionId) : undefined
  return sessionId ? <SessionView key={sessionId} subjectId={subjectId} sessionId={sessionId} /> : <StartView subjectId={subjectId} />
}

/** Start a session for a file or a topic; the caller opens it. Topics the files don't cover come back as suggestions. */
function useStart(subjectId: number) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [notCovered, setNotCovered] = useState<NotCovered | null>(null)
  const [error, setError] = useState<string | null>(null)
  async function start(body: { topic: string } | { material_id: number }, replace = false) {
    setBusy(true)
    setError(null)
    try {
      const result = await startSession(subjectId, body)
      if ('covered' in result) setNotCovered(result)
      else navigate(`/subjects/${subjectId}/explain/${result.id}`, { replace })
    } catch (e) {
      setError(e instanceof ApiError && e.status !== 500 ? e.message : 'We couldn’t start the session. Try again in a moment.')
    } finally {
      setBusy(false)
    }
  }
  return { start, busy, notCovered, error }
}

function StartView({ subjectId }: { subjectId: number }) {
  const overview = useOverview(subjectId)
  const [params] = useSearchParams()
  const { start, busy, notCovered, error } = useStart(subjectId)
  const [topic, setTopic] = useState('')
  const fileParam = Number(params.get('file'))
  const autoStarted = useRef(false)
  // Home's "Explain it" suggestion links here with ?file=, so start that file straight away
  useEffect(() => {
    if (fileParam && overview.data?.files.some(f => f.id === fileParam) && !autoStarted.current) {
      autoStarted.current = true
      start({ material_id: fileParam }, true)
    }
  })

  const data = overview.data
  return (
    <div className="page-content explain-page">
      <Link className="workspace-breadcrumb" to={`/subjects/${subjectId}?tab=explain`}>
        <span className="back-chevron"><Icon name="chevronRight" size={13} /></span>Back to subject
      </Link>
      <div className="explain-intro">
        <XpAvatar />
        <div>
          <h1>Explain it back</h1>
          <p>Pick a topic and explain it in your own words, out loud or in writing. XP checks each point against your notes.</p>
        </div>
      </div>

      {overview.isPending && <div className="skeleton-stack"><Skeleton /><Skeleton /><Skeleton /></div>}
      {overview.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load this subject.</p>
          <Button variant="secondary" onClick={() => overview.refetch()}>Try again</Button>
        </div>
      )}
      {data && !data.files_ready && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="upload" /></span>
          <h2>Upload notes first</h2>
          <p>XP checks your explanation against the files in this subject, and none are ready yet.</p>
          <Link className={buttonClass()} to={`/subjects/${subjectId}?upload=1`}><Icon name="upload" />Upload a file</Link>
        </div>
      )}
      {data?.files_ready && (
        <div className="explain-start">
          {busy && fileParam ? <ProgressBar label="Starting your session" /> : null}
          {notCovered && (
            <div className="explain-not-covered" role="alert">
              <strong>“{notCovered.topic}” isn’t in your files</strong>
              <p>{notCovered.suggestions.length ? 'XP can only check what your notes cover. These topics are close:' : 'XP can only check what your notes cover. Try a topic from the list below.'}</p>
              <div className="topic-chips">
                {notCovered.suggestions.map(s => <button type="button" key={s} disabled={busy} onClick={() => start({ topic: s })}>{s}</button>)}
              </div>
            </div>
          )}
          {error && <p className="explain-error" role="alert">{error}</p>}

          <form className="explain-topic-form" onSubmit={e => { e.preventDefault(); if (topic.trim().length >= 3) start({ topic: topic.trim() }) }}>
            <label htmlFor="explain-topic">Type your own topic</label>
            <div>
              <input id="explain-topic" value={topic} maxLength={200} placeholder="For example, how B-trees stay balanced" onChange={e => setTopic(e.target.value)} />
              <Button type="submit" variant="ai" disabled={busy || topic.trim().length < 3}>Start</Button>
            </div>
          </form>

          {data.topics.length > 0 && (
            <section>
              <h2>Topics from your files</h2>
              <div className="topic-chips">
                {data.topics.map(t => <button type="button" key={t} disabled={busy} onClick={() => start({ topic: t })}>{t}</button>)}
              </div>
            </section>
          )}

          <section>
            <h2>Or explain a whole file</h2>
            <div className="explain-files">
              {data.files.map(f => (
                <button type="button" key={f.id} disabled={busy} onClick={() => start({ material_id: f.id })}>
                  <Icon name="file" /><span>{f.name}</span><Icon name="chevronRight" size={15} />
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function StudentText({ turn }: { turn: Turn }) {
  return (
    <div className="user-message explain-said">
      {turn.mode === 'voice' && <span className="explain-said-mode"><Icon name="mic" size={14} />You said</span>}
      {turn.student_text}
    </div>
  )
}

function TurnView({ turn, voiceTurn, onPlay }: { turn: Turn; voiceTurn: boolean; onPlay: () => void }) {
  return (
    <motion.article className="explain-turn" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.24 }}>
      <StudentText turn={turn} />
      <div className="xp-message">
        <XpAvatar small />
        <div>
          <p className="explain-reply">{turn.reply}</p>
          {voiceTurn && <button type="button" className="explain-play" onClick={onPlay}><Icon name="volume" size={15} />Play reply</button>}
          {turn.answer && (
            <div className="explain-answer">
              <strong>From your notes</strong>
              <p>{turn.answer}</p>
            </div>
          )}
        </div>
      </div>
      <Marks marks={turn.marks} />
    </motion.article>
  )
}

function LimitBanner({ limit }: { limit: Limit }) {
  const at = resetTime(limit.resets_at)
  return (
    <div className="rate-banner explain-limit" role="alert">
      <Icon name="clock" size={15} />
      <span><strong>You’ve used today’s {limit.limit} checks.</strong> {at ? `You can explain again at ${at}.` : 'You can explain again tomorrow.'}</span>
    </div>
  )
}

type Stage = { name: 'record' } | { name: 'sending'; progress: number } | { name: 'hearing' } | { name: 'review'; text: string } | { name: 'checking'; text: string; mode: 'voice' | 'text' }

function SessionView({ subjectId, sessionId }: { subjectId: number; sessionId: number }) {
  const session = useSession(sessionId)
  const send = useSendTurn(sessionId)
  const finish = useFinish(sessionId)
  const remove = useDeleteSession(subjectId)
  const navigate = useNavigate()
  const once = useOneAtATime()
  const again = useStart(subjectId)
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')
  const [stage, setStage] = useState<Stage>({ name: 'record' })
  const [problem, setProblem] = useState<string | null>(null)
  const [limitHit, setLimitHit] = useState<Limit | null>(null)
  const [muted, setMuted] = useState(readMuted)
  const [deleting, setDeleting] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => stopSpeaking, [])

  const data = session.data
  useEffect(() => {
    if (stage.name !== 'record') end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [stage.name, data?.turns.length])

  if (session.isPending) return <div className="page-content explain-page"><div className="skeleton-stack"><Skeleton /><Skeleton /><Skeleton /></div></div>
  if (session.isError || !data) {
    const gone = session.error instanceof ApiError && session.error.status === 404
    return (
      <div className="page-content explain-page">
        <div className="inline-error" role="alert">
          <p>{gone ? 'This session was deleted.' : 'We couldn’t load this session.'}</p>
          {gone
            ? <Link className={buttonClass('secondary')} to={`/subjects/${subjectId}/explain`}>Start a new one</Link>
            : <Button variant="secondary" onClick={() => session.refetch()}>Try again</Button>}
        </div>
      </div>
    )
  }

  const limit = limitHit ?? (data.limit.used >= data.limit.limit ? data.limit : null)
  const round = data.turns.length + 1
  const play = (turn: Turn) => speak(turn, data.voice).then(ok => { if (!ok) toast('error', 'Couldn’t play the reply', 'Your device has no voice for reading aloud. The reply is shown as text.') })

  async function check(text: string, mode: 'voice' | 'text') {
    setProblem(null)
    setStage({ name: 'checking', text, mode })
    try {
      const next = await send.mutateAsync({ text, mode })
      setDraft('')
      setStage({ name: 'record' })
      const latest = next.turns[next.turns.length - 1]
      if (latest && mode === 'voice' && !muted) speak(latest, next.voice)
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) setLimitHit({ ...data!.limit, used: data!.limit.limit, ...(e.data as Partial<Limit>) })
      else setProblem(e instanceof ApiError && e.status < 500 ? e.message : 'XP couldn’t check that just now. Your explanation is still here; try again in a moment.')
      if (mode === 'text') setDraft(text)
      setStage(mode === 'voice' ? { name: 'review', text } : { name: 'record' })
    }
  }

  async function heard(take: Take) {
    setProblem(null)
    setStage({ name: 'sending', progress: 0 })
    try {
      const { text } = await transcribe(sessionId, take.clip, fraction => setStage(fraction < 1 ? { name: 'sending', progress: fraction } : { name: 'hearing' }))
      setStage({ name: 'review', text })
    } catch (e) {
      setProblem(e instanceof ApiError && e.message ? e.message : 'XP couldn’t turn that recording into text. Record again, or type instead.')
      setStage({ name: 'record' })
    }
  }

  const confirmDelete = () => once(() => remove.mutateAsync(sessionId).then(
    () => { setDeleting(false); navigate(`/subjects/${subjectId}?tab=explain`, { replace: true }); toast('success', 'Session deleted') },
    () => { toast('error', 'Couldn’t delete the session', 'Try again in a moment.'); throw new Error('not deleted') },
  ), { final: true })
  const explainAgain = () => again.start(data.material_id ? { material_id: data.material_id } : { topic: data.topic })
  const toggleMute = () => { const next = !muted; setMuted(next); saveMuted(next); if (next) stopSpeaking() }
  const busy = stage.name === 'sending' || stage.name === 'hearing' || stage.name === 'checking'
  const prompt = data.turns.length === 0
    ? `Explain ${data.material_name ? `the main ideas in ${data.topic}` : data.topic} as if you were teaching it. Aim for 30 seconds to 3 minutes.`
    : 'Answer XP’s question, or add anything you missed.'

  return (
    <div className="page-content explain-page">
      <Link className="workspace-breadcrumb" to={`/subjects/${subjectId}?tab=explain`}>
        <span className="back-chevron"><Icon name="chevronRight" size={13} /></span>{data.subject_name}
      </Link>
      <header className="explain-header">
        <div>
          <h1>{data.topic}</h1>
          <p>{data.finished ? 'Finished' : `Round ${Math.min(round, data.max_rounds)} of ${data.max_rounds}`} · Explain it back</p>
        </div>
        <div className="explain-header-actions">
          {data.voice && !data.finished && (
            <IconButton icon={muted ? 'volumeOff' : 'volume'} label={muted ? 'Turn XP’s voice on' : 'Turn XP’s voice off'} aria-pressed={muted} onClick={toggleMute} />
          )}
          <IconButton icon="trash" label="Delete this session" onClick={() => setDeleting(true)} />
          {!data.finished && data.turns.length > 0 && (
            <Button variant="secondary" disabled={busy || finish.isPending} onClick={() => finish.mutate()}>Finish</Button>
          )}
        </div>
      </header>

      {data.finished && data.summary && <SessionSummary session={data} onAgain={explainAgain} busy={again.busy} />}
      {again.error && <p className="explain-error" role="alert">{again.error}</p>}

      <div className="explain-thread">
        {data.finished && data.turns.length > 0 && <h2 className="explain-thread-title">Round by round</h2>}
        {data.turns.map(t => <TurnView key={t.id} turn={t} voiceTurn={t.mode === 'voice'} onPlay={() => play(t)} />)}
        {!data.finished && <MissingSoFar points={data.key_points} />}
        {stage.name === 'checking' && (
          <>
            <div className="user-message explain-said">{stage.text}</div>
            <div className="explain-progress" role="status"><span>Checking against your notes…</span><ProgressBar label="Checking against your notes" /></div>
          </>
        )}
        <div ref={end} />
      </div>

      {!data.finished && (limit ? <LimitBanner limit={limit} /> : (
        <section className="explain-composer" aria-label="Your explanation">
          {problem && <p className="explain-error" role="alert">{problem}</p>}
          {stage.name === 'sending' && (
            <div className="explain-progress" role="status">
              <span>Sending your recording… {Math.round(stage.progress * 100)}%</span>
              <ProgressBar value={Math.round(stage.progress * 100)} label="Sending your recording" />
            </div>
          )}
          {stage.name === 'hearing' && (
            <div className="explain-progress" role="status"><span>Turning your recording into text…</span><ProgressBar label="Turning your recording into text" /></div>
          )}
          {stage.name === 'review' && (
            <form className="explain-heard" onSubmit={e => { e.preventDefault(); if (stage.text.trim()) check(stage.text.trim(), 'voice') }}>
              <label htmlFor="explain-heard">What XP heard</label>
              <p>Fix any words XP got wrong, or record again.</p>
              <textarea id="explain-heard" value={stage.text} maxLength={MAX} rows={5} onChange={e => setStage({ name: 'review', text: e.target.value })} />
              <div className="explain-actions">
                <Button variant="secondary" icon="mic" onClick={() => setStage({ name: 'record' })}>Record again</Button>
                <Button type="submit" variant="ai" disabled={!stage.text.trim()}>Check my explanation</Button>
              </div>
            </form>
          )}
          {stage.name === 'record' && !typing && (
            <>
              <Recorder prompt={prompt} onTake={heard} onType={() => setTyping(true)} />
              <p className="explain-privacy">Your recording is turned into text by OpenAI, then deleted. Only the text is kept. <Link to="/privacy">Privacy</Link></p>
            </>
          )}
          {stage.name === 'record' && typing && (
            <form className="explain-typed" onSubmit={e => { e.preventDefault(); if (draft.trim()) check(draft.trim(), 'text') }}>
              <label htmlFor="explain-typed">{prompt}</label>
              <textarea id="explain-typed" value={draft} maxLength={MAX} rows={5} placeholder="Explain it in your own words…" onChange={e => setDraft(e.target.value)} />
              <div className="explain-actions">
                <Button variant="ghost" icon="mic" onClick={() => setTyping(false)}>Speak instead</Button>
                <Button type="submit" variant="ai" disabled={!draft.trim()}>Check my explanation</Button>
              </div>
            </form>
          )}
        </section>
      ))}

      <ConfirmDialog open={deleting} title="Delete this session?" confirmLabel="Delete session" icon="trash"
        busy={remove.isPending} onCancel={() => setDeleting(false)} onConfirm={confirmDelete}>
        <p>“{data.topic}”, what you said and XP’s feedback will be removed. This can’t be undone.</p>
      </ConfirmDialog>
    </div>
  )
}

