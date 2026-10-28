import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { Link } from 'react-router'
import { api, useMe } from '../../lib/api'
import { reveal } from '../../lib/motion'
import { SubjectIcon } from '../../ui/SubjectIcon'
import { timeAgo } from '../../lib/format'
import { CountUp } from '../../ui/CountUp'
import { Icon } from '../../ui/Icon'
import { Button, Skeleton, buttonClass, type Tone } from '../../ui/primitives'
import '../../styles/home.css'

type Suggestion = {
  kind: 'review' | 'weak_quiz' | 'untried_quiz' | 'knowledge_gap' | 'empty_subject'
  title: string
  reason: string
  url: string
  subject_id: number
  quiz_id: number | null
}
type Home = {
  due: { count: number; subjects: number; minutes: number }
  suggestions: Suggestion[]
  recent_chats: { id: number; title: string; subject_id: number; subject_name: string; last_activity: string }[]
  subjects: { id: number; name: string; materials_count: number; due_count: number; last_quiz_score: number | null }[]
}

const MotionLink = motion.create(Link)

/** Where a suggestion goes inside the app; null while its screen still lives on the old pages. */
const inApp = (s: Suggestion): string | null =>
  s.kind === 'review' ? `/review?subject=${s.subject_id}`
    : s.kind === 'weak_quiz' ? `/quizzes/${s.quiz_id}/start?fresh=1` // a retake asks new questions
    : s.kind === 'untried_quiz' ? `/quizzes/${s.quiz_id}/start`
    : s.kind === 'knowledge_gap' || s.kind === 'empty_subject' ? `/subjects/${s.subject_id}?upload=1`
    : null

const ACTIONS: Record<Suggestion['kind'], { label: string; tone: Tone }> = {
  weak_quiz: { label: 'Retake', tone: 'warning' },
  review: { label: 'Review', tone: 'primary' },
  knowledge_gap: { label: 'Upload', tone: 'ai' },
  untried_quiz: { label: 'Start quiz', tone: 'success' },
  empty_subject: { label: 'Upload', tone: 'neutral' },
}

export function greeting(hour = new Date().getHours()) {
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export function todayLabel(date = new Date()) {
  const weekday = date.toLocaleDateString('en-GB', { weekday: 'long' })
  const day = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })
  return `${weekday}, ${day}`.toUpperCase()
}

function ReviewHero({ due }: { due: Home['due'] }) {
  const caughtUp = due.count === 0
  return (
    <section className="review-hero">
      <div>
        <span className="review-symbol"><Icon name="repeat" /></span>
        <div>
          <span className="eyebrow">CARDS TO REVIEW</span>
          {caughtUp ? <h2>Nothing to review now</h2> : <h2><CountUp value={due.count} /> flashcard{due.count === 1 ? '' : 's'} to review</h2>}
          <p>
            {caughtUp
              ? 'New cards appear when you upload files. Cards you have reviewed come back when it’s time.'
              : `Across ${due.subjects} subject${due.subjects === 1 ? '' : 's'} · about ${due.minutes} minute${due.minutes === 1 ? '' : 's'}`}
          </p>
        </div>
      </div>
      {!caughtUp && <Link className={buttonClass()} to="/review"><Icon name="play" />Start review</Link>}
    </section>
  )
}

function TodaySkeleton() {
  return (
    <div className="today-grid" aria-busy="true" aria-label="Loading your day">
      <div className="today-main">
        <section className="review-hero"><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton className="skeleton-value" /><Skeleton /></div></section>
        <div className="next-list">
          {[0, 1, 2].map(i => <div className="next-item" key={i}><Skeleton className="skeleton-avatar" /><div className="skeleton-stack"><Skeleton /><Skeleton className="skeleton-label" /></div></div>)}
        </div>
      </div>
      <aside className="today-side"><section className="conversations-card"><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton /><Skeleton /></div></section></aside>
    </div>
  )
}

export function Today() {
  const me = useMe()
  const home = useQuery({ queryKey: ['home'], queryFn: () => api<Home>('/api/home/') })
  const data = home.data

  return (
    <div className="page-content today-page">
      <div className="page-intro">
        <div>
          <p className="overline">{todayLabel()}</p>
          {me.data ? <h1>{greeting()}, {me.data.first_name || me.data.username}</h1> : <h1><Skeleton className="skeleton-value" /></h1>}
          <p>Here’s the most useful work to do today.</p>
        </div>
      </div>

      {home.isPending && <TodaySkeleton />}
      {home.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your day. Check your connection and try again.</p>
          <Button variant="secondary" onClick={() => home.refetch()}>Try again</Button>
        </div>
      )}

      {data && (
        <div className="today-grid">
          <div className="today-main">
            {data.subjects.length === 0 ? (
              <section className="first-run">
                <span className="empty-icon"><Icon name="book" /></span>
                <div>
                  <h2>Start with your first subject</h2>
                  <p>A subject holds the files for one class, like Biology. Then upload a PDF or Word file and ask XP about it.</p>
                  <Link className={buttonClass()} to="/subjects?new=1"><Icon name="plus" />Create your first subject</Link>
                </div>
              </section>
            ) : <ReviewHero due={data.due} />}

            <section className="dashboard-section">
              <div className="section-heading">
                <div>
                  <h2>Suggested next steps</h2>
                  <p>Ranked by what will help you most right now.</p>
                </div>
              </div>
              <div className="next-list">
                {data.suggestions.length === 0 && (
                  <p className="list-empty">Nothing to suggest yet. Upload a file to a subject and XP will plan your next steps.</p>
                )}
                {data.suggestions.map((s, i) => {
                  const action = ACTIONS[s.kind]
                  return (
                    <motion.article className="next-item" key={`${s.kind}-${s.subject_id}-${s.quiz_id}`} {...reveal(i)}>
                      <span className={`rank rank--${action.tone}`}>{i + 1}</span>
                      <div>
                        <strong>{s.title}</strong>
                        <p>{s.reason}</p>
                      </div>
                      {inApp(s)
                        ? <Link className={buttonClass(i === 0 ? 'primary' : 'secondary')} to={inApp(s)!}>{action.label}</Link>
                        : <a className={buttonClass(i === 0 ? 'primary' : 'secondary')} href={s.url}>{action.label}</a>}
                    </motion.article>
                  )
                })}
              </div>
            </section>

            {data.subjects.length > 0 && (
              <section className="dashboard-section">
                <div className="section-heading">
                  <div>
                    <h2>Your subjects</h2>
                    <p>Cards to review and your latest quiz score in each subject.</p>
                  </div>
                  <Link to="/subjects">View all <Icon name="arrow" size={15} /></Link>
                </div>
                <div className="home-subjects">
                  {data.subjects.slice(0, 3).map((s, i) => (
                    <MotionLink className="home-subject" key={s.id} to={`/subjects/${s.id}`} {...reveal(i)}>
                      <SubjectIcon id={s.id} name={s.name} />
                      <div>
                        <strong>{s.name}</strong>
                        <span>{s.materials_count} file{s.materials_count === 1 ? '' : 's'}</span>
                      </div>
                      <dl>
                        <div><dt>To review</dt><dd>{s.due_count}</dd></div>
                        <div><dt>Last quiz</dt><dd>{s.last_quiz_score === null ? '—' : `${s.last_quiz_score}%`}</dd></div>
                      </dl>
                      <Icon name="chevronRight" size={16} />
                    </MotionLink>
                  ))}
                </div>
              </section>
            )}
          </div>

          <aside className="today-side">
            <section className="conversations-card">
              <div className="section-heading">
                <div>
                  <h2>Continue chatting</h2>
                  <p>Recent XP conversations</p>
                </div>
                {data.recent_chats.length > 0 && <Link to="/subjects">View all</Link>}
              </div>
              {data.recent_chats.length === 0 && (
                <p className="list-empty">No conversations yet. Open a subject and ask XP about your materials.</p>
              )}
              {data.recent_chats.map(c => (
                <Link className="conversation-row" key={c.id} to={`/subjects/${c.subject_id}/chat/${c.id}`}>
                  <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
                  <div>
                    <strong>{c.title}</strong>
                    <span>{c.subject_name} · {timeAgo(c.last_activity)}</span>
                  </div>
                  <Icon name="chevronRight" size={14} />
                </Link>
              ))}
            </section>
          </aside>
        </div>
      )}
    </div>
  )
}
