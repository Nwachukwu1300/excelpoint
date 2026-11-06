import { Link } from 'react-router'
import { Evidence } from '../chat/Thread'
import { Icon } from '../../ui/Icon'
import { ProgressRing } from '../../ui/ProgressRing'
import { Badge, buttonClass, type Tone } from '../../ui/primitives'
import { percent, type KeyPoint, type Mark, type Passage, type Session, type Verdict } from './api'

const LOOK: Record<Verdict, { label: string; tone: Tone }> = {
  correct: { label: 'Correct', tone: 'success' },
  wrong: { label: 'Not quite', tone: 'danger' },
  not_in_notes: { label: 'Not in your notes', tone: 'neutral' },
}

const noop = () => {}

/** The passage behind a mark, with the deciding words highlighted (the shared chat evidence block). */
function Source({ passage, match }: { passage: Passage; match: string }) {
  return <Evidence chunks={[{ ...passage, similarity_score: 0 }]} answer={match} onOpen={noop} />
}

function MarkRow({ mark }: { mark: Mark }) {
  const look = LOOK[mark.verdict]
  return (
    <li className={`explain-mark explain-mark--${mark.verdict}`}>
      <div className="explain-mark-head">
        <Badge tone={look.tone}>{look.label}</Badge>
        <p>{mark.sentence}</p>
      </div>
      {mark.note && <p className="explain-note"><strong>Your notes say:</strong> {mark.note}</p>}
      {mark.verdict === 'not_in_notes' && <p className="explain-note">This might be true, but your files don’t cover it, so XP couldn’t check it.</p>}
      {mark.passage && <Source passage={mark.passage} match={mark.quote || mark.note || mark.sentence} />}
    </li>
  )
}

const count = (marks: Mark[], verdict: Verdict) => marks.filter(m => m.verdict === verdict).length

/** Every statement from one turn, marked against the student's files. */
export function Marks({ marks }: { marks: Mark[] }) {
  if (marks.length === 0) return null
  const parts = (['correct', 'wrong', 'not_in_notes'] as const)
    .map(v => [count(marks, v), LOOK[v].label.toLowerCase()] as const).filter(([n]) => n > 0).map(([n, l]) => `${n} ${l}`)
  return (
    <section className="explain-marks" aria-label="Checked against your notes">
      <h3>Checked against your notes <span>{parts.join(' · ')}</span></h3>
      <ul>{marks.map((m, i) => <MarkRow key={i} mark={m} />)}</ul>
    </section>
  )
}

export function PointList({ points }: { points: KeyPoint[] }) {
  return (
    <ul className="explain-points">
      {points.map(k => (
        <li key={k.id}>
          <p>{k.point}</p>
          <Source passage={k.passage} match={k.point} />
        </li>
      ))}
    </ul>
  )
}

/** Key points not mentioned yet. Closed by default so the student can try first. */
export function MissingSoFar({ points }: { points: KeyPoint[] }) {
  const missing = points.filter(k => !k.covered)
  if (missing.length === 0) return null
  return (
    <details className="explain-missing">
      <summary>{missing.length === 1 ? '1 key point you haven’t mentioned yet' : `${missing.length} key points you haven’t mentioned yet`}</summary>
      <PointList points={missing} />
    </details>
  )
}

function verdict(coverage: number | null, accuracy: number | null) {
  const low = Math.min(coverage ?? 0, accuracy ?? 1)
  return low >= 0.8 ? 'You know this well' : low >= 0.5 ? 'Good progress' : 'Keep going'
}

/** The end of a session: coverage and accuracy, then what they nailed, got wrong and missed. */
export function SessionSummary({ session, onAgain, busy }: { session: Session; onAgain: () => void; busy: boolean }) {
  const summary = session.summary!
  const coverage = percent(session.coverage)
  const accuracy = percent(session.accuracy)
  const covered = session.key_points.filter(k => k.covered).length
  const checked = summary.nailed.length + summary.wrong.length
  return (
    <section className="explain-summary" aria-labelledby="summary-title">
      <div className="explain-hero">
        <div className="explain-rings">
          {coverage !== null && <ProgressRing value={coverage} label="covered" />}
          {accuracy !== null && <ProgressRing value={accuracy} label="accurate" />}
        </div>
        <div>
          <h2 id="summary-title">{verdict(session.coverage, session.accuracy)}</h2>
          <p>
            {session.key_points.length > 0 && `You covered ${covered} of ${session.key_points.length} key points. `}
            {checked > 0 ? `${summary.nailed.length} of ${checked} statements XP could check were right.` : 'XP had nothing it could check against your notes.'}
          </p>
        </div>
        <div className="explain-hero-actions">
          <button type="button" className={buttonClass('ai')} onClick={onAgain} disabled={busy}><Icon name="mic" />Explain it again</button>
          <Link className={buttonClass('secondary')} to={`/subjects/${session.subject_id}?tab=explain`}>Back to subject</Link>
        </div>
      </div>
      {summary.nailed.length > 0 && <SummaryGroup title="What you nailed" marks={summary.nailed} />}
      {summary.wrong.length > 0 && <SummaryGroup title="What to fix" marks={summary.wrong} />}
      {summary.missed.length > 0 && (
        <div className="explain-group">
          <h3>What you missed</h3>
          <p>Important points from your notes you didn’t mention.</p>
          <PointList points={summary.missed} />
        </div>
      )}
      {summary.not_in_notes.length > 0 && <SummaryGroup title="Not in your notes" marks={summary.not_in_notes} />}
    </section>
  )
}

function SummaryGroup({ title, marks }: { title: string; marks: Mark[] }) {
  return (
    <div className="explain-group">
      <h3>{title}</h3>
      <ul className="explain-marks-list">{marks.map((m, i) => <MarkRow key={i} mark={m} />)}</ul>
    </div>
  )
}
