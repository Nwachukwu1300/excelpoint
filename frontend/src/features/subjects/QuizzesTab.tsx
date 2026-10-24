import { motion } from 'motion/react'
import { plural } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { Link } from 'react-router'
import { Icon } from '../../ui/Icon'
import { Button, Skeleton, buttonClass } from '../../ui/primitives'
import { useQuizzes } from './api'

const pct = (n: number | null) => (n === null ? '—' : `${n}%`)

export function QuizzesTab({ subjectId }: { subjectId: number }) {
  const quizzes = useQuizzes(subjectId)
  return (
    <div>
      <div className="tab-toolbar">
        <div>
          <h2>Quizzes</h2>
          <p>Test your recall with questions grounded in each file.</p>
        </div>
        <Link className={buttonClass('secondary')} to={`/quizzes/history?subject=${subjectId}`}>Quiz history</Link>
      </div>
      {quizzes.isPending && (
        <div className="quiz-list" aria-busy="true" aria-label="Loading quizzes">
          {[0, 1].map(i => <div className="quiz-row" key={i}><Skeleton className="skeleton-avatar" /><div className="skeleton-stack"><Skeleton /><Skeleton className="skeleton-label" /></div></div>)}
        </div>
      )}
      {quizzes.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load the quizzes.</p>
          <Button variant="secondary" onClick={() => quizzes.refetch()}>Try again</Button>
        </div>
      )}
      {quizzes.data?.length === 0 && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="layers" /></span>
          <h2>No quizzes yet</h2>
          <p>XP writes a quiz for every file it processes. Upload a file to get your first one.</p>
        </div>
      )}
      {!!quizzes.data?.length && (
        <div className="quiz-list">
          {quizzes.data.map((q, i) => (
            <motion.article className="quiz-row" key={q.id} {...reveal(i)}>
              <span className="quiz-file-icon"><Icon name="file" /></span>
              <div className="quiz-title">
                <h3>{q.material_name ?? q.title}</h3>
                <p>{plural(q.question_count, 'question')}</p>
              </div>
              <dl>
                <div><dt>Last</dt><dd>{pct(q.last_score)}</dd></div>
                <div><dt>Best</dt><dd>{pct(q.best_score)}</dd></div>
                <div><dt>Attempts</dt><dd>{q.attempts ? plural(q.attempts, 'attempt') : 'No attempts'}</dd></div>
              </dl>
              <div className="quiz-actions">
                <Link className={buttonClass('secondary')} to={`/quizzes/${q.id}/start`}>Start</Link>
                <Link className={buttonClass('ai')} to={`/quizzes/${q.id}/start?fresh=1`}><Icon name="sparkles" size={14} /> New questions</Link>
              </div>
            </motion.article>
          ))}
        </div>
      )}
    </div>
  )
}
