import { motion } from 'motion/react'
import { useState } from 'react'
import { plural } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { Link } from 'react-router'
import { Icon } from '../../ui/Icon'
import { Badge, Button, Skeleton, buttonClass } from '../../ui/primitives'
import { useFlashcards, type Flashcard } from './api'

const ALL = 'All materials'

/** "Due today" or "In 3 days"; never-reviewed cards are due now. */
export function dueLabel(card: Flashcard, now = Date.now()) {
  if (!card.due_at) return { label: 'Review today', due: true }
  const days = Math.ceil((new Date(card.due_at).getTime() - now) / 86_400_000)
  if (days <= 0) return { label: 'Due today', due: true }
  return { label: days === 1 ? 'Tomorrow' : `In ${days} days`, due: false }
}

export function FlashcardsTab({ subjectId, dueCount }: { subjectId: number; dueCount: number }) {
  const cards = useFlashcards(subjectId)
  const [filter, setFilter] = useState(ALL)
  const sources = [...new Set(cards.data?.map(c => c.material_name).filter((n): n is string => !!n))]
  const shown = cards.data?.filter(c => filter === ALL || c.material_name === filter) ?? []

  return (
    <div>
      <div className="tab-toolbar">
        <div>
          <h2>Flashcards</h2>
          <p>{cards.data ? `${dueCount} to review today · ${plural(cards.data.length, 'card')} in total` : 'Loading cards…'}</p>
        </div>
        <div className="toolbar-actions">
          {sources.length > 1 && (
            <div className="select-wrap compact-select">
              <select aria-label="Filter by material" value={filter} onChange={e => setFilter(e.target.value)}>
                <option>{ALL}</option>
                {sources.map(s => <option key={s}>{s}</option>)}
              </select>
              <Icon name="chevronDown" size={14} />
            </div>
          )}
          {dueCount > 0
            ? <Link className={buttonClass()} to={`/review?subject=${subjectId}`}>Review {plural(dueCount, 'card')}</Link>
            : <Button disabled>No cards to review</Button>}
        </div>
      </div>
      {cards.isPending && (
        <div className="flashcard-grid" aria-busy="true" aria-label="Loading flashcards">
          {[0, 1, 2].map(i => <div className="flashcard-preview" key={i}><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton /><Skeleton /></div></div>)}
        </div>
      )}
      {cards.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load the flashcards.</p>
          <Button variant="secondary" onClick={() => cards.refetch()}>Try again</Button>
        </div>
      )}
      {cards.data?.length === 0 && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="repeat" /></span>
          <h2>No flashcards yet</h2>
          <p>XP makes flashcards from every file it processes. Upload a file to start reviewing.</p>
        </div>
      )}
      {shown.length > 0 && (
        <div className="flashcard-grid">
          {shown.map((card, i) => {
            const { label, due } = dueLabel(card)
            return (
              <motion.article className="flashcard-preview" key={card.id} {...reveal(i)}>
                <div>
                  <Badge tone={due ? 'warning' : 'neutral'}>{label}</Badge>
                  {card.material_name && <span>{card.material_name}</span>}
                </div>
                <h3>{card.question}</h3>
                <p>{card.answer}</p>
              </motion.article>
            )
          })}
        </div>
      )}
    </div>
  )
}
