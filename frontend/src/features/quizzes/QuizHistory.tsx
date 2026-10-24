import { Link, useSearchParams } from 'react-router'
import { useMe } from '../../lib/api'
import { shortDate } from '../../lib/format'
import { Icon } from '../../ui/Icon'
import { Badge, Button, ProgressBar, Skeleton } from '../../ui/primitives'
import { useHistory } from './api'
import '../../styles/quiz.css'

export function QuizHistory() {
  const [params, setParams] = useSearchParams()
  const subject = params.get('subject')
  const history = useHistory(subject)
  const me = useMe()
  const data = history.data

  return (
    <div className="page-content">
      <div className="page-intro">
        <div>
          <p className="overline">QUIZZES</p>
          <h1>Quiz history</h1>
          <p>Every attempt, score, and subject in one place.</p>
        </div>
        <div className="select-wrap compact-select">
          <select aria-label="Filter by subject" value={subject ?? ''} onChange={e => setParams(e.target.value ? { subject: e.target.value } : {}, { replace: true })}>
            <option value="">All subjects</option>
            {me.data?.subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <Icon name="chevronDown" size={14} />
        </div>
      </div>

      {history.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your quiz history.</p>
          <Button variant="secondary" onClick={() => history.refetch()}>Try again</Button>
        </div>
      )}
      {history.isPending && (
        <section className="performance-card" aria-busy="true"><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton /><Skeleton /></div></section>
      )}
      {data?.attempts.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="layers" /></span>
          <h2>No quizzes taken yet</h2>
          <p>Open a subject’s Quizzes tab to test yourself. Your scores will build up here.</p>
          <Link className="button button--secondary" to="/subjects">Go to subjects</Link>
        </div>
      )}
      {!!data?.attempts.length && (
        <>
          <section className="performance-card">
            <div>
              <h2>Performance by subject</h2>
              <p>Average score across all attempts</p>
            </div>
            {data.subjects.map(s => (
              <div className="performance-row" key={s.id}>
                <span>{s.name}</span>
                <ProgressBar value={s.average} label={`${s.name} average`} />
                <strong>{s.average}%</strong>
              </div>
            ))}
          </section>
          <div className="table-wrap history-table">
            <table>
              <thead>
                <tr><th>Quiz</th><th>Subject</th><th>Date</th><th>Score</th><th>Details</th></tr>
              </thead>
              <tbody>
                {data.attempts.map(a => (
                  <tr key={a.id}>
                    <td><strong>{a.quiz_title}</strong>{a.fresh && <Badge tone="ai">NEW QUESTIONS</Badge>}</td>
                    <td>{a.subject_name}</td>
                    <td>{shortDate(a.finished_at)}</td>
                    <td><Badge tone={a.score >= 70 ? 'success' : 'warning'}>{a.score}%</Badge></td>
                    <td><Link className="table-link" to={`/quiz-attempts/${a.id}/results`}>View details</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
