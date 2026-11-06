import { motion } from 'motion/react'
import { Link } from 'react-router'
import { shortDate } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { Icon } from '../../ui/Icon'
import { Badge, Button, Skeleton, buttonClass } from '../../ui/primitives'
import { percent, useOverview, type SessionRow } from './api'
import '../../styles/explain.css'

/** How coverage changed since the last finished session on the same topic. */
function trend(row: SessionRow, older: SessionRow[]) {
  const before = older.find(s => s.finished && s.coverage !== null && s.topic.toLowerCase() === row.topic.toLowerCase())
  if (!row.finished || row.coverage === null || !before) return null
  const now = percent(row.coverage)!, then = percent(before.coverage)!
  return now > then ? { text: `Up from ${then}%`, tone: 'success' as const }
    : now < then ? { text: `Down from ${then}%`, tone: 'warning' as const }
    : { text: 'Same as last time', tone: 'neutral' as const }
}

export function ExplainTab({ subjectId }: { subjectId: number }) {
  const overview = useOverview(subjectId)
  const sessions = overview.data?.sessions ?? []
  return (
    <>
      <div className="tab-toolbar">
        <div>
          <h2>Explain it back</h2>
          <p>Explain a topic in your own words, out loud or in writing. XP checks each point against your files.</p>
        </div>
        <Link className={buttonClass('ai')} to={`/subjects/${subjectId}/explain`}><Icon name="mic" />Start explaining</Link>
      </div>
      {overview.isPending && <div className="skeleton-stack"><Skeleton /><Skeleton /><Skeleton /></div>}
      {overview.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your sessions.</p>
          <Button variant="secondary" onClick={() => overview.refetch()}>Try again</Button>
        </div>
      )}
      {overview.data && sessions.length === 0 && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="mic" /></span>
          <h2>No explanations yet</h2>
          <p>{overview.data.files_ready
            ? 'Pick a topic, explain it as if you were teaching it, and see what you got right, what to fix and what you missed.'
            : 'Upload notes first. XP checks your explanation against the files in this subject.'}</p>
        </div>
      )}
      {sessions.length > 0 && (
        <div className="explain-history">
          {sessions.map((s, i) => {
            const change = trend(s, sessions.slice(i + 1))
            return (
              <motion.div key={s.id} {...reveal(i)}>
                <Link to={`/subjects/${subjectId}/explain/${s.id}`}>
                  <div>
                    <strong>{s.topic}</strong>
                    <span>
                      {shortDate(s.created_at)} · {s.finished
                        ? [s.coverage !== null && `${percent(s.coverage)}% covered`, s.accuracy !== null && `${percent(s.accuracy)}% accurate`].filter(Boolean).join(' · ') || 'Finished'
                        : `Not finished · ${s.rounds} round${s.rounds === 1 ? '' : 's'}`}
                    </span>
                  </div>
                  {change && <span className="explain-trend"><Badge tone={change.tone}>{change.text}</Badge></span>}
                  <Icon name="chevronRight" size={16} />
                </Link>
              </motion.div>
            )
          })}
        </div>
      )}
    </>
  )
}
