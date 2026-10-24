import { motion } from 'motion/react'
import { useEffect, useRef } from 'react'
import { plural } from '../../lib/format'
import { ConfidencePill } from '../../ui/AnswerBadges'
import { IconButton, ProgressBar } from '../../ui/primitives'
import { describeAnswer, type ChatMessage, type SourceChunk } from './api'
import { chunkLabel, fileName } from './Thread'

const ext = (name: string) => (name.split('.').pop() ?? '').toUpperCase().slice(0, 4)
const excerpt = (text: string) => (text.length > 280 ? `${text.slice(0, 277).trimEnd()}…` : text)

export function SourcesPanel({ message, focus, onClose }: { message?: ChatMessage; focus: SourceChunk | null; onClose: () => void }) {
  const a = message ? describeAnswer(message) : null
  const chunks = a?.chunks ?? []
  const list = useRef<HTMLDivElement>(null)

  // A clicked citation scrolls its excerpt into view
  useEffect(() => {
    if (!focus) return
    list.current?.querySelector<HTMLElement>(`[data-chunk="${CSS.escape(chunkLabel(focus))}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [focus])

  return (
    <motion.aside
      className="sources-panel"
      aria-label="Sources"
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16, transition: { duration: 0.12 } }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="sources-head">
        <div>
          <strong>Sources</strong>
          <span>{chunks.length ? `${plural(chunks.length, 'excerpt')} used` : 'Nothing cited yet'}</span>
        </div>
        <IconButton icon="close" label="Close sources" onClick={onClose} />
      </div>
      {a?.confidence !== null && a?.confidence !== undefined && (
        <div className="sources-confidence"><span>Answer confidence</span><ConfidencePill value={a.confidence} /></div>
      )}
      <div ref={list}>
        {chunks.length === 0 && (
          <p className="sources-empty">When XP answers from your files, the exact excerpts it used appear here.</p>
        )}
        {chunks.map((c, i) => {
          const label = chunkLabel(c)
          const pct = Math.round(Math.max(0, Math.min(1, c.similarity_score)) * 100)
          return (
            <article key={`${label}-${i}`} data-chunk={label} className={`source-excerpt ${focus && chunkLabel(focus) === label ? 'is-focused' : ''}`}>
              <div>
                <span className="file-type">{ext(c.material_name)}</span>
                <div>
                  <strong>{fileName(c.material_name)}</strong>
                  <span>{c.chunk_index !== undefined ? `Chunk ${c.chunk_index + 1}` : 'Excerpt'}</span>
                </div>
              </div>
              <div className="similarity">
                <span>Similarity</span>
                <ProgressBar value={pct} label={`Similarity ${pct}%`} />
                <strong>{pct}%</strong>
              </div>
              <p>“{excerpt(c.content)}”</p>
            </article>
          )
        })}
      </div>
    </motion.aside>
  )
}
