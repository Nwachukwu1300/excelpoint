import { motion } from 'motion/react'
import { Link } from 'react-router'
import { CitationChip, VerificationBadge } from '../../ui/AnswerBadges'
import { Icon } from '../../ui/Icon'
import { Markdown } from '../../ui/Markdown'
import { describeAnswer, type ChatMessage, type SourceChunk } from './api'

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

/** Stored names include the upload folder (subject_materials/…); people only need the file name. */
export const fileName = (path: string) => path.split('/').pop() || path

export const chunkLabel = (c: SourceChunk) => `${fileName(c.material_name)}${c.chunk_index !== undefined ? ` · part ${c.chunk_index + 1}` : ''}`

/** One chip per distinct excerpt, at most three; the Sources panel lists the rest. */
function citations(chunks: SourceChunk[]) {
  const seen = new Set<string>()
  return chunks.filter(c => { const k = chunkLabel(c); return !seen.has(k) && seen.add(k) }).slice(0, 3)
}

const enter = { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const } }

export function UserBubble({ text, animate }: { text: string; animate?: boolean }) {
  return <motion.div className="user-message" {...(animate ? enter : {})}>{text}</motion.div>
}

export function Thinking() {
  return (
    <motion.div className="thinking" role="status" {...enter}>
      <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
      <span className="shimmer-text">XP is thinking…</span>
      <i /><i /><i />
    </motion.div>
  )
}

/** The answer while it streams in: plain growing text with a blinking caret. */
export function StreamingAnswer({ text }: { text: string }) {
  return (
    <div className="xp-message" aria-live="polite" aria-busy="true">
      <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
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
      <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
      <div>
        <div className="answer-body">
          <Markdown text={a.body} />
          {a.verified === false && (
            <div className="verification-note">Parts of this answer could not be fully verified against your materials.</div>
          )}
        </div>
        <div className="answer-footer">
          {citations(a.chunks).map(c => <CitationChip key={chunkLabel(c)} label={chunkLabel(c)} onClick={() => onCite(c)} />)}
          {a.verified !== undefined && <VerificationBadge verified={a.verified} />}
          <span>{time(message.timestamp)}</span>
          {message.trace_url && <Link to={message.trace_url.replace(/\/$/, '')}>How was this answered?</Link>}
        </div>
      </div>
    </motion.div>
  )
}
