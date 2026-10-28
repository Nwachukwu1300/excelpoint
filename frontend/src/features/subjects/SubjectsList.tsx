import { motion } from 'motion/react'
import { Link, useSearchParams } from 'react-router'
import { plural, timeAgo } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { SubjectIcon } from '../../ui/SubjectIcon'
import { Icon } from '../../ui/Icon'
import { Button, Skeleton } from '../../ui/primitives'
import { useSubjects } from './api'
import { NewSubjectModal } from './NewSubjectModal'
import '../../styles/subjects.css'

export function SubjectsList() {
  const subjects = useSubjects()
  const [params, setParams] = useSearchParams()
  const creating = params.get('new') === '1'
  const setCreating = (on: boolean) => setParams(on ? { new: '1' } : {}, { replace: true })

  return (
    <div className="page-content">
      <div className="page-intro">
        <div>
          <h1>Subjects</h1>
          <p>Each subject keeps its files, quizzes and flashcards together.</p>
        </div>
        <Button icon="plus" onClick={() => setCreating(true)}>New subject</Button>
      </div>

      {subjects.isPending && (
        <div className="subjects-list-grid" aria-busy="true" aria-label="Loading subjects">
          {[0, 1, 2].map(i => (
            <div className="subject-list-card" key={i}>
              <Skeleton className="skeleton-avatar" />
              <div className="skeleton-stack" style={{ marginTop: 18 }}><Skeleton className="skeleton-label" /><Skeleton /></div>
            </div>
          ))}
        </div>
      )}
      {subjects.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your subjects. Check your connection and try again.</p>
          <Button variant="secondary" onClick={() => subjects.refetch()}>Try again</Button>
        </div>
      )}
      {subjects.data?.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="book" /></span>
          <h2>Create your first subject</h2>
          <p>A subject holds the files for one class or topic. XP turns each file into a summary, flashcards and a quiz.</p>
          <Button icon="plus" onClick={() => setCreating(true)}>New subject</Button>
        </div>
      )}
      {!!subjects.data?.length && (
        <div className="subjects-list-grid">
          {subjects.data.map((s, i) => (
            <motion.article className="subject-list-card" key={s.id} {...reveal(i)}>
              <div className="subject-list-top">
                <SubjectIcon id={s.id} name={s.name} />
              </div>
              <h2>{s.name}</h2>
              <p>{plural(s.materials_count, 'file')} · Updated {timeAgo(s.updated_at)}</p>
              <div className="subject-card-stats">
                <div><strong>{s.due_count}</strong><span>to review</span></div>
                <div><strong>{s.last_quiz_score === null ? '—' : `${s.last_quiz_score}%`}</strong><span>last quiz</span></div>
              </div>
              <Link className="button button--secondary full-width" to={`/subjects/${s.id}`}>
                Open subject <Icon name="arrow" size={15} />
              </Link>
            </motion.article>
          ))}
          <motion.button type="button" className="add-subject-card" onClick={() => setCreating(true)} {...reveal(subjects.data.length)}>
            <span><Icon name="plus" /></span>
            <strong>New subject</strong>
            <small>Create a space for your materials</small>
          </motion.button>
        </div>
      )}
      <NewSubjectModal open={creating} onClose={() => setCreating(false)} />
    </div>
  )
}
