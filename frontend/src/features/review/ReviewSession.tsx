import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../../lib/api'
import { plural } from '../../lib/format'
import { Icon } from '../../ui/Icon'
import { Button, Logo, ProgressBar, Skeleton, buttonClass } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import '../../styles/review.css'

type Card = { id: number; question: string; answer: string; subject_id: number; subject_name: string; material_name: string | null; next_days: Record<string, number> }
type Queue = { due_count: number; subject: { id: number; name: string } | null; grades: { grade: number; label: string }[]; cards: Card[] }

/** "1 day", "15 days", "2 months". */
export const interval = (days: number) => (days >= 60 ? `${Math.round(days / 30)} months` : days >= 30 ? '1 month' : plural(days, 'day'))

const AGAIN = 1
const GRADE_CLASS: Record<number, string> = { [AGAIN]: 'grade-again', 5: 'grade-easy' }

export function ReviewSession() {
  const [params] = useSearchParams()
  const subjectParam = params.get('subject')
  const queryClient = useQueryClient()
  const queue = useQuery({
    queryKey: ['review-queue', subjectParam],
    queryFn: () => api<Queue>(`/api/review/queue/${subjectParam ? `?subject=${subjectParam}` : ''}`),
    staleTime: Infinity, // one snapshot per session; grading changes it
    refetchOnWindowFocus: false,
    gcTime: 0,
  })
  const [cards, setCards] = useState<Card[] | null>(null)
  const [pos, setPos] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [reviewed, setReviewed] = useState(0)
  useEffect(() => { if (queue.data && !cards) setCards(queue.data.cards) }, [queue.data, cards])

  const grade = useMutation({
    mutationFn: ({ card, value }: { card: Card; value: number }) =>
      api('/api/review/grade/', { method: 'POST', body: { flashcard_id: card.id, grade: value } }),
    onError: (_, { card }) => {
      setCards(list => (list ? [...list, card] : list)) // try this card again at the end
      toast('error', 'Couldn’t save that grade', 'The card will come up again at the end of this session.')
    },
  })

  const card = cards?.[pos]
  const finished = !!cards && pos >= cards.length
  const exitTo = subjectParam ? `/subjects/${subjectParam}` : '/'

  const answer = useCallback((value: number) => {
    if (!card || !revealed) return
    grade.mutate({ card, value }) // saved in the background: the next card shows straight away
    if (value === AGAIN) setCards(list => (list ? [...list, card] : list)) // forgotten: see it again before this session ends
    setRevealed(false)
    setPos(p => p + 1)
    if (value !== AGAIN) setReviewed(n => n + 1)
  }, [card, revealed, grade])

  // Space/Enter shows the answer; 1-4 grade it.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!card || e.metaKey || e.ctrlKey || e.altKey || (e.target as HTMLElement).closest('input, textarea, select')) return
      if (!revealed && (e.key === ' ' || e.key === 'Enter')) { e.preventDefault(); setRevealed(true) }
      const choice = queue.data?.grades[Number(e.key) - 1]
      if (revealed && choice) { e.preventDefault(); answer(choice.grade) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [card, revealed, answer, queue.data])

  // Counts on Home, the sidebar and the workspace change after a session
  useEffect(() => {
    if (!finished || !reviewed) return
    for (const key of [['me'], ['home'], ['subjects'], ['flashcards']]) queryClient.invalidateQueries({ queryKey: key })
  }, [finished, reviewed, queryClient])

  if (finished || queue.data?.cards.length === 0) {
    return (
      <div className="review-focus done-review">
        <Logo />
        <motion.span className="success-burst" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 380, damping: 18 }}>
          <Icon name="check" />
        </motion.span>
        <h1>Nothing to review now</h1>
        <p>
          {reviewed
            ? `You reviewed ${plural(reviewed, 'card')}. Cards come back on a schedule that stretches each time you remember them.`
            : 'New cards appear when you upload files. Cards you have reviewed come back when it’s time to practise them again.'}
        </p>
        <Link className={buttonClass()} to="/">Back to Home</Link>
      </div>
    )
  }

  const total = cards?.length ?? 0
  return (
    <div className="review-focus">
      <header className="review-focus-head">
        <Logo />
        <div>
          <strong>{card ? `Card ${pos + 1} of ${total}` : 'Loading cards…'}</strong>
          <ProgressBar value={total ? (pos / total) * 100 : 0} label="Review progress" />
        </div>
        <Link className="icon-button" to={exitTo} aria-label="Exit review" title="Exit review"><Icon name="close" /></Link>
      </header>
      <main className="review-card-stage">
        {queue.isError && (
          <div className="inline-error" role="alert">
            <p>We couldn’t load your cards.</p>
            <Button variant="secondary" onClick={() => queue.refetch()}>Try again</Button>
          </div>
        )}
        {queue.isPending && (
          <div className="study-card" aria-busy="true" aria-label="Loading cards"><div className="skeleton-stack" style={{ width: '70%' }}><Skeleton className="skeleton-label" /><Skeleton className="skeleton-value" /><Skeleton /></div></div>
        )}
        {card && (
          <>
            <motion.div
              key={`${card.id}-${revealed}`}
              className={`study-card ${revealed ? 'is-revealed' : ''}`}
              initial={{ opacity: 0, y: revealed ? 4 : 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              aria-live="polite"
            >
              <span className="eyebrow">{revealed ? 'ANSWER' : card.subject_name.toUpperCase()}</span>
              <h1>{revealed ? card.answer : card.question}</h1>
              {card.material_name && <span className="card-source">{card.material_name}</span>}
            </motion.div>
            {/* In "Show answer", detail 2 is the second click of a double click on the grade before: not a request to reveal */}
            {!revealed ? (
              <Button onClick={e => { if (e.detail <= 1) setRevealed(true) }}>Show answer</Button>
            ) : (
              <div className="grade-area">
                <p>How well did you remember?</p>
                <div>
                  {queue.data?.grades.map(g => (
                    <button type="button" key={g.grade} className={GRADE_CLASS[g.grade] ?? ''} onClick={() => answer(g.grade)}>
                      <strong>{g.label}</strong>
                      <span>{g.grade === AGAIN ? 'This session' : interval(card.next_days[g.grade] ?? 1)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <p className="review-keys" aria-hidden="true">{revealed ? 'Press 1–4 to grade' : 'Press Space to show the answer'}</p>
          </>
        )}
      </main>
    </div>
  )
}
