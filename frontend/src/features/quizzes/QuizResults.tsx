import { motion } from 'motion/react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMe } from '../../lib/api'
import { plural } from '../../lib/format'
import { reveal, spring } from '../../lib/motion'
import { Icon } from '../../ui/Icon'
import { Badge, Button, ProgressRing, Skeleton, buttonClass } from '../../ui/primitives'
import { useResults, type Results } from './api'
import '../../styles/quiz.css'

const verdict = (score: number) => (score >= 80 ? 'Great work' : score >= 60 ? 'Good progress' : 'Keep going')

/** True when the timer, not the student, ended the attempt (small slack for the submit round trip). */
export const timeRanOut = (r: Pick<Results, 'quiz' | 'started_at' | 'finished_at'>) =>
  !!r.quiz.time_limit && new Date(r.finished_at).getTime() - new Date(r.started_at).getTime() >= r.quiz.time_limit * 60_000 - 5_000

export function QuizResults() {
  const attemptId = Number(useParams().attemptId)
  const results = useResults(attemptId)
  const me = useMe()
  const r = results.data
  const [only, setOnly] = useState<'missed' | 'all' | null>(null)

  if (results.isError) {
    return (
      <div className="page-content results-page">
        <div className="inline-error" role="alert">
          <p>We couldn’t load these results. {results.error.message}</p>
          <Button variant="secondary" onClick={() => results.refetch()}>Try again</Button>
        </div>
      </div>
    )
  }
  if (!r) {
    return (
      <div className="page-content results-page" aria-busy="true">
        <div className="results-hero"><Skeleton className="skeleton-avatar" /><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton className="skeleton-value" /></div></div>
      </div>
    )
  }

  const name = me.data?.first_name
  const missed = r.questions.filter(q => !q.is_correct)
  const unanswered = r.questions.filter(q => !q.your_answer).length
  const view = only ?? (missed.length ? 'missed' : 'all') // open on what to study next
  const shown = view === 'missed' ? missed : r.questions
  return (
    <div className="page-content results-page">
      <div className="results-hero">
        <ProgressRing value={r.score} label="score" />
        <div>
          <Badge tone={r.passed ? 'success' : 'warning'}>{r.passed ? 'Passed' : 'Not passed yet'}</Badge>
          <h1>{verdict(r.score)}{name ? `, ${name}` : ''}</h1>
          <p>
            You earned <strong>{r.earned_points} of {plural(r.total_points, 'point')}</strong> and answered{' '}
            <strong>{plural(r.correct_count, 'question')} correctly</strong>
            {' '}on {r.quiz.material_name ?? r.quiz.title}.
            {unanswered > 0 && timeRanOut(r) && ` Time ran out before you answered ${plural(unanswered, 'question')}.`}
            {!r.passed && ' Look at the questions you missed below, then try new questions.'}
          </p>
        </div>
        <div className="results-actions">
          <Link className={buttonClass('ai')} to={`/quizzes/${r.quiz.id}/start?fresh=1`}><Icon name="sparkles" size={15} /> Retake with new questions</Link>
          <Link className={buttonClass('secondary')} to={`/subjects/${r.quiz.subject_id}?tab=quizzes`}>Back to subject</Link>
        </div>
      </div>
      <div className="review-heading">
        <div>
          <h2>Question review</h2>
          <p>See what you understood and where to focus next.</p>
        </div>
        {missed.length > 0 && missed.length < r.questions.length && (
          <div className="segmented-control" role="group" aria-label="Which questions to show">
            {(['missed', 'all'] as const).map(v => (
              <button type="button" key={v} aria-pressed={view === v} className={view === v ? 'is-active' : ''} onClick={() => setOnly(v)}>
                {view === v && <motion.span layoutId="results-pill" className="segment-pill" transition={spring.morph} />}
                <span>{v === 'missed' ? `Missed (${missed.length})` : `All (${r.questions.length})`}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {shown.map((q, i) => (
        <motion.article className={`result-question ${q.is_correct ? 'is-correct' : q.your_answer ? 'is-incorrect' : 'is-unanswered'}`} key={q.id} {...reveal(i)}>
          <div className="result-number">
            <span aria-label={q.is_correct ? 'Correct' : q.your_answer ? 'Incorrect' : 'Not answered'}><Icon name={q.is_correct ? 'check' : q.your_answer ? 'close' : 'clock'} size={16} /></span>
            <strong>Question {r.questions.indexOf(q) + 1}</strong>
            <small>{plural(q.points, 'point')}</small>
          </div>
          <h3>{q.text}</h3>
          <div className="answer-review">
            <div>
              <span>Your answer</span>
              <strong>{q.your_answer || <em className="no-answer">Not answered</em>}</strong>
            </div>
            {!q.is_correct && q.correct_answer && (
              <div>
                <span>Correct answer</span>
                <strong>{q.correct_answer}</strong>
              </div>
            )}
          </div>
          {q.explanation && (
            <div className="explanation">
              <strong>Explanation</strong>
              <p>{q.explanation}</p>
            </div>
          )}
        </motion.article>
      ))}
    </div>
  )
}
