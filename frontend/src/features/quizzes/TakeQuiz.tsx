import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { plural } from '../../lib/format'
import { Icon } from '../../ui/Icon'
import { Badge, Button, Logo, ProgressBar, buttonClass } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import { loadDraft, saveDraft, startAttempt, submitAttempt, typeLabel, useAttempt, type Attempt } from './api'
import '../../styles/quiz.css'

const SLOW_AFTER_MS = 45_000

function Generating({ attempt, onStandard }: { attempt: Attempt; onStandard: () => void }) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (slow) return
    const timer = window.setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => window.clearTimeout(timer)
  }, [slow])
  const back = `/subjects/${attempt.quiz.subject_id}?tab=quizzes`
  if (slow) {
    return (
      <div className="generation-state">
        <span className="empty-icon warning-icon"><Icon name="clock" /></span>
        <h1>Taking longer than expected</h1>
        <p>XP hasn’t finished writing your new questions yet. Nothing has been lost.</p>
        <div>
          <Button variant="secondary" onClick={() => setSlow(false)}>Keep waiting</Button>
          <Button onClick={onStandard}>Take the standard quiz instead</Button>
        </div>
      </div>
    )
  }
  return (
    <div className="generation-state" role="status">
      <span className="xp-avatar"><Icon name="sparkles" /></span>
      <Badge tone="ai">GENERATING WITH XP</Badge>
      <h1>Writing fresh questions</h1>
      <p>Reading {attempt.quiz.material_name ?? 'your material'} and balancing question difficulty…</p>
      <div className="generation-progress"><span /></div>
      <small>This usually takes 10–30 seconds</small>
      <Link className={buttonClass('ghost')} to={back}>Cancel</Link>
    </div>
  )
}

/** Time left as mm:ss (and whether it's under a minute), or null without a time limit. Submits at zero. */
function useCountdown(attempt: Attempt | undefined, onExpire: () => void) {
  const [now, setNow] = useState(Date.now())
  const limit = attempt?.quiz.time_limit
  useEffect(() => {
    if (!limit) return
    const t = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(t)
  }, [limit])
  const left = limit && attempt ? Math.max(0, new Date(attempt.started_at).getTime() + limit * 60_000 - now) : null
  const expired = left === 0
  const fired = useRef(false)
  useEffect(() => { if (expired && !fired.current) { fired.current = true; onExpire() } }, [expired, onExpire])
  if (left === null) return null
  const s = Math.ceil(left / 1000)
  return { text: `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`, low: s < 60 }
}

export function TakeQuiz() {
  const attemptId = Number(useParams().attemptId)
  const attempt = useAttempt(attemptId)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>(() => loadDraft(attemptId))
  const [submitting, setSubmitting] = useState(false)

  const data = attempt.data
  useEffect(() => { if (data?.status === 'completed') navigate(`/quiz-attempts/${attemptId}/results`, { replace: true }) }, [data?.status, attemptId, navigate])
  useEffect(() => { if ((location.state as { fellBack?: boolean } | null)?.fellBack) toast('error', 'Fresh questions are unavailable', 'XP couldn’t start writing new questions, so here’s the standard quiz.') }, [location.state])

  const answer = (questionId: string, value: string) => {
    setAnswers(a => { const next = { ...a, [questionId]: value }; saveDraft(attemptId, next); return next })
  }

  const submit = async () => {
    if (submitting) return
    setSubmitting(true)
    try {
      const results = await submitAttempt(attemptId, answers)
      saveDraft(attemptId, null)
      queryClient.setQueryData(['quiz-results', attemptId], results)
      for (const key of [['quizzes'], ['subjects'], ['home'], ['quiz-history']]) queryClient.invalidateQueries({ queryKey: key })
      navigate(`/quiz-attempts/${attemptId}/results`, { replace: true })
    } catch (e) {
      setSubmitting(false)
      toast('error', 'Couldn’t submit your quiz', `${(e as Error).message}. Your answers are still here; try again.`)
    }
  }
  const remaining = useCountdown(data?.status === 'ready' ? data : undefined, submit)

  const standard = async () => {
    if (!data) return
    try { navigate(`/quiz-attempts/${(await startAttempt(data.quiz.id, false)).id}`, { replace: true }) }
    catch (e) { toast('error', 'Couldn’t start the quiz', (e as Error).message) }
  }

  if (attempt.isError) {
    return (
      <div className="generation-state">
        <h1>We couldn’t open this quiz</h1>
        <p>{attempt.error.message}</p>
        <div><Button variant="secondary" onClick={() => attempt.refetch()}>Try again</Button><Link className={buttonClass()} to="/">Back to Today</Link></div>
      </div>
    )
  }
  if (!data) return <div className="generation-state" aria-busy="true"><p>Loading quiz…</p></div>
  if (data.status === 'generating') return <Generating attempt={data} onStandard={standard} />
  if (data.status === 'failed' || data.status === 'abandoned') {
    return (
      <div className="generation-state">
        <span className="empty-icon warning-icon"><Icon name="close" /></span>
        <h1>{data.status === 'failed' ? 'XP couldn’t write new questions' : 'This attempt was replaced'}</h1>
        <p>{data.status === 'failed' ? 'Something went wrong while reading your material. The standard quiz is ready to take.' : 'You started a newer attempt on this quiz.'}</p>
        <div>
          {data.status === 'failed' && <Button variant="secondary" onClick={() => navigate(`/quizzes/${data.quiz.id}/start?fresh=1`, { replace: true })}>Try again</Button>}
          <Button onClick={standard}>Take the standard quiz</Button>
        </div>
      </div>
    )
  }

  const questions = data.questions
  const exitTo = `/subjects/${data.quiz.subject_id}?tab=quizzes`
  const q = questions[Math.min(index, questions.length - 1)]
  const last = index >= questions.length - 1
  const unanswered = questions.filter(qq => !answers[qq.id]?.trim()).length

  return (
    <div className="quiz-focus">
      <header className="focus-header">
        <Logo />
        <div>
          <strong>{data.quiz.material_name ?? data.quiz.title}</strong>
          <span>{data.quiz.subject_name}</span>
        </div>
        <Link to={exitTo} aria-label="Save and exit">Save &amp; exit <Icon name="close" size={15} /></Link>
      </header>
      <main className="quiz-stage">
        {!q ? (
          <div className="empty-state empty-state--compact">
            <h2>This quiz has no questions yet</h2>
            <p>Try fresh questions from XP instead.</p>
            <Link className={buttonClass('ai')} to={`/quizzes/${data.quiz.id}/start?fresh=1`}><Icon name="sparkles" />New questions</Link>
          </div>
        ) : (
          <>
            <div className="quiz-progress-head">
              <span>Question {index + 1} of {questions.length}</span>
              {remaining && <span className={remaining.low ? 'is-low' : ''}><Icon name="clock" size={14} /> {remaining.text} remaining</span>}
            </div>
            <ProgressBar value={((index + 1) / questions.length) * 100} label="Quiz progress" />
            <motion.section key={q.id} className="question-card" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
              <div className="question-meta">
                <Badge>{typeLabel[q.type]}</Badge>
                <span>{plural(q.points, 'point')}</span>
              </div>
              <h1 id={`q-${q.id}`}>{q.text}</h1>
              {q.choices.length ? (
                <div className="answer-options" role="radiogroup" aria-labelledby={`q-${q.id}`}>
                  {q.choices.map((c, i) => (
                    <button type="button" role="radio" aria-checked={answers[q.id] === c.id} key={c.id}
                      className={answers[q.id] === c.id ? 'is-selected' : ''} onClick={() => answer(q.id, c.id)}>
                      <span>{String.fromCharCode(65 + i)}</span>
                      {c.text}
                    </button>
                  ))}
                </div>
              ) : (
                <textarea className="short-answer" rows={5} placeholder="Write your answer here…" aria-labelledby={`q-${q.id}`}
                  value={answers[q.id] ?? ''} onChange={e => answer(q.id, e.target.value)} />
              )}
            </motion.section>
            <div className="quiz-navigation">
              <Button variant="secondary" disabled={index === 0} onClick={() => setIndex(i => i - 1)}>Previous</Button>
              <div className="question-dots" aria-hidden="true">
                {questions.map((qq, i) => <span key={qq.id} className={i === index ? 'is-active' : answers[qq.id] ? 'is-done' : ''} />)}
              </div>
              {last
                ? <Button onClick={submit} disabled={submitting}>{submitting ? 'Submitting…' : 'Submit quiz'} <Icon name="arrow" size={15} /></Button>
                : <Button onClick={() => setIndex(i => i + 1)}>Next <Icon name="arrow" size={15} /></Button>}
            </div>
            {last && unanswered > 0 && (
              <p className="unanswered-note">{plural(unanswered, 'question')} still unanswered. Unanswered questions score zero.</p>
            )}
          </>
        )}
      </main>
    </div>
  )
}
