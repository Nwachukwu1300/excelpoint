import { XpAvatar } from '../../ui/primitives'
import { motion } from 'motion/react'
import { Link } from 'react-router'
import { useState } from 'react'
import { VerificationBadge } from '../../ui/AnswerBadges'
import { Icon } from '../../ui/Icon'
import { Markdown } from '../../ui/Markdown'
import { describeAnswer, type ChatMessage, type SourceChunk } from './api'

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

/** Stored names include the upload folder (subject_materials/…); people only need the file name. */
export const fileName = (path: string) => path.split('/').pop() || path

export const chunkLabel = (c: SourceChunk) => `${fileName(c.material_name)}${c.chunk_index !== undefined ? ` · part ${c.chunk_index + 1}` : ''}`

/** Each distinct passage once, in the order the search ranked them. */
function passages(chunks: SourceChunk[]) {
  const seen = new Set<string>()
  return chunks.filter(c => { const k = chunkLabel(c); return !seen.has(k) && seen.add(k) })
}

const COMMON = new Set(['that', 'this', 'with', 'from', 'have', 'they', 'their', 'them', 'then', 'than', 'which', 'into', 'about',
  'also', 'your', 'what', 'when', 'where', 'there', 'these', 'those', 'were', 'been', 'will', 'each', 'such', 'only', 'more', 'most', 'some'])
const words = (text: string) => new Set((text.toLowerCase().match(/[\p{L}\p{N}]{4,}/gu) ?? []).filter(w => !COMMON.has(w)))

/** The passage with the words it shares with the answer marked, so the match is visible at a glance. */
export function markShared(passage: string, answer: string) {
  const shared = words(answer)
  return passage.split(/([\p{L}\p{N}]+)/u).map((part, i) =>
    shared.has(part.toLowerCase()) ? <mark key={i}>{part}</mark> : part)
}

/** The passage from the sentence that shares the most words with the answer, so the short view shows the match. */
export function fromBestSentence(passage: string, answer: string) {
  const shared = words(answer)
  const sentences = passage.match(/[^.!?]+[.!?]*\s*/g) ?? [passage]
  let best = 0, bestScore = -1
  sentences.forEach((s, i) => {
    const score = [...words(s)].filter(w => shared.has(w)).length
    if (score > bestScore) { best = i; bestScore = score }
  })
  return best === 0 ? passage : '…' + sentences.slice(best).join('').trimStart()
}

/** The evidence for an answer: the best passage from the student's own file, right under the answer. */
function Evidence({ chunks, answer, onOpen }: { chunks: SourceChunk[]; answer: string; onOpen: (c: SourceChunk) => void }) {
  const [open, setOpen] = useState(false)
  const [best, ...rest] = passages(chunks)
  if (!best) return null
  const whole = best.content.trim()
  const short = fromBestSentence(whole, answer)
  const long = short.length > 240 || short !== whole
  return (
    <figure className="answer-evidence">
      <figcaption>
        <Icon name="file" size={15} />
        <span>From <strong>{fileName(best.material_name)}</strong></span>
      </figcaption>
      <blockquote className={long && !open ? 'is-clamped' : ''}>{markShared(open ? whole : short, answer)}</blockquote>
      <div className="evidence-actions">
        {long && <button type="button" aria-expanded={open} onClick={() => setOpen(o => !o)}>{open ? 'Show less' : 'Show the whole passage'}</button>}
        {rest.length > 0 && (
          <button type="button" onClick={() => onOpen(best)}>{rest.length === 1 ? 'See 1 more passage' : `See ${rest.length} more passages`}</button>
        )}
      </div>
    </figure>
  )
}

const enter = { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const } }

export function UserBubble({ text, animate }: { text: string; animate?: boolean }) {
  return <motion.div className="user-message" {...(animate ? enter : {})}>{text}</motion.div>
}

export function Thinking() {
  return (
    <motion.div className="thinking" role="status" {...enter}>
      <XpAvatar small />
      <span className="shimmer-text">XP is thinking…</span>
      <i /><i /><i />
    </motion.div>
  )
}

/** The answer while it streams in: plain growing text with a blinking caret. */
export function StreamingAnswer({ text }: { text: string }) {
  return (
    <div className="xp-message" aria-live="polite" aria-busy="true">
      <XpAvatar small />
      <div><div className="answer-body"><Markdown text={text} caret={<span className="caret" aria-hidden="true" />} /></div></div>
    </div>
  )
}

export function Answer({ message, subjectId, selected, onCite, animate }: {
  message: ChatMessage
  subjectId: number
  selected: boolean
  onCite: (chunk: SourceChunk) => void
  animate?: boolean
}) {
  const a = describeAnswer(message)
  if (a.notFound) {
    return (
      <motion.div className="not-found-answer" {...(animate ? enter : {})}>
        <span className="info-icon" aria-hidden="true">i</span>
        <div>
          <strong>{a.noFilesReady ? 'No files ready yet' : 'Not in your materials'}</strong>
          <p>{a.body}</p>
          {a.noFilesReady
            ? <Link className="button button--secondary" to={`/subjects/${subjectId}`}><Icon name="file" />Check your files</Link>
            : <Link className="button button--secondary" to={`/subjects/${subjectId}?upload=1`}><Icon name="upload" />Upload files</Link>}
        </div>
      </motion.div>
    )
  }
  return (
    <motion.div className={`xp-message ${selected ? 'is-selected' : ''}`} {...(animate ? enter : {})}>
      <XpAvatar small />
      <div>
        <div className="answer-body">
          <Markdown text={a.body} />
          {a.verified === false && (
            <div className="verification-note">Some parts of this answer could not be checked against your files.</div>
          )}
        </div>
        <Evidence chunks={a.chunks} answer={a.body} onOpen={onCite} />
        <div className="answer-footer">
          {a.verified !== undefined && <VerificationBadge verified={a.verified} />}
          <span>{time(message.timestamp)}</span>
          {message.trace_url && <Link to={message.trace_url.replace(/\/$/, '')}>How was this answered?</Link>}
        </div>
      </div>
    </motion.div>
  )
}
