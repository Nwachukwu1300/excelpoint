import { motion } from 'motion/react'
import { Link, useParams } from 'react-router'
import { useMe } from '../../lib/api'
import { plural } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { Icon } from '../../ui/Icon'
import { Badge, Button, ProgressRing, Skeleton, buttonClass } from '../../ui/primitives'
import { useResults } from './api'
import '../../styles/quiz.css'

const verdict = (score: number) => (score >= 80 ? 'Great work' : score >= 60 ? 'Good progress' : 'Keep going')

export function QuizResults() {
  const attemptId = Number(useParams().attemptId)
  const results = useResults(attemptId)
  const me = useMe()
  const r = results.data

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
  return (
    <div className="page-content results-page">
      <div className="results-hero">
        <ProgressRing value={r.score} label="score" />
        <div>
          <Badge tone={r.passed ? 'success' : 'warning'}>{r.passed ? 'QUIZ COMPLETE' : 'BELOW PASS MARK'}</Badge>
          <h1>{verdict(r.score)}{name ? `, ${name}` : ''}</h1>
          <p>
            You earned <strong>{r.earned_points} of {plural(r.total_points, 'point')}</strong> and answered{' '}
            <strong>{plural(r.correct_count, 'question')} correctly</strong>
            {' '}on {r.quiz.material_name ?? r.quiz.title}.
          </p>
        </div>
        <div className="results-actions">
          <Link className={buttonClass('ai')} to={`/quizzes/${r.quiz.id}/start?fresh=1`}><Icon name="sparkles" size={15} /> Retake with new questions</Link>
          <Link className={buttonClass('secondary')} to={`/subjects/${r.quiz.subject_id}?tab=quizzes`}>Back to subject</Link>
        </div>
      </div>
      <div className="review-heading">
        <h2>Question review</h2>
        <p>See what you understood and where to focus next.</p>
      </div>
      {r.questions.map((q, i) => (
        <motion.article className={`result-question ${q.is_correct ? 'is-correct' : 'is-incorrect'}`} key={q.id} {...reveal(i)}>
          <div className="result-number">
            <span aria-label={q.is_correct ? 'Correct' : 'Incorrect'}><Icon name={q.is_correct ? 'check' : 'close'} size={16} /></span>
            <strong>Question {i + 1}</strong>
            <small>{plural(q.points, 'point')}</small>
          </div>
          <h3>{q.text}</h3>
          <div className="answer-review">
            <div>
              <span>Your answer</span>
              <strong>{q.your_answer || <em className="no-answer">No answer</em>}</strong>
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
