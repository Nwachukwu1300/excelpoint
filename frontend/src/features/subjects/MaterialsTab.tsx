import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { plural, shortDate } from '../../lib/format'
import { reveal, spring } from '../../lib/motion'
import { Link } from 'react-router'
import { Icon } from '../../ui/Icon'
import { MoreMenu } from '../../ui/Menu'
import { Modal } from '../../ui/Modal'
import { Badge, Button, ProgressBar, Skeleton, StatusChip } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import { parseSummary, useDeleteMaterial, useMaterials, type Material } from './api'

const typeLabel = (m: Material) => (m.filename.split('.').pop() ?? m.file_type).toUpperCase().slice(0, 4)

function Summary({ material }: { material: Material }) {
  const { intro, points } = parseSummary(material.summary)
  return (
    <div className="material-summary">
      <div className="summary-heading">
        <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
        <div>
          <Badge tone="ai">AI SUMMARY</Badge>
          <h3>Core concepts from this material</h3>
        </div>
      </div>
      {intro.length === 0 && points.length === 0 && <p>No summary yet. XP writes one after processing a file.</p>}
      {intro.map((line, i) => <p key={i}>{line}</p>)}
      {points.length > 0 && <ul>{points.map((p, i) => <li key={i}>{p}</li>)}</ul>}
      {material.quiz_id && (
        <Link className="summary-link" to={`/quizzes/${material.quiz_id}/start`}>Take the quiz for this file <Icon name="arrow" size={14} /></Link>
      )}
    </div>
  )
}

function MaterialRow({ material, index, onDelete, onQuizzes }: { material: Material; index: number; onDelete: () => void; onQuizzes: () => void }) {
  const [open, setOpen] = useState(false)
  const ready = material.status === 'COMPLETED'
  const busy = material.status === 'PENDING' || material.status === 'PROCESSING'
  return (
    <motion.article className={`workspace-material material--${material.status.toLowerCase()}`} {...reveal(index)}>
      <div className="material-row-main">
        <span className="file-type">{typeLabel(material)}</span>
        <div className="material-primary">
          <strong title={material.filename}>{material.filename}</strong>
          <span>Uploaded {shortDate(material.created_at)}</span>
          {material.status === 'FAILED' && <small className="failure-copy">Processing failed. Delete this file and upload it again.</small>}
          {busy && (
            <div className="inline-processing">
              <ProgressBar label={`Processing ${material.filename}`} />
              <small>Creating summary, flashcards and quiz…</small>
            </div>
          )}
        </div>
        <StatusChip status={material.status} />
        <div className="material-actions">
          {ready && (
            <>
              <button type="button" aria-expanded={open} onClick={() => setOpen(o => !o)}>
                <Icon name="sparkles" size={14} /> AI summary <Icon name={open ? 'chevronDown' : 'chevronRight'} size={14} />
              </button>
              {material.quiz_id && <button type="button" onClick={onQuizzes}>Quiz</button>}
            </>
          )}
          {!busy && <MoreMenu label={`More actions for ${material.filename}`} items={[{ label: 'Delete file', danger: true, onSelect: onDelete }]} />}
        </div>
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="summary-wrap"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={spring.gentle}
          >
            <Summary material={material} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  )
}

export function MaterialsTab({ subjectId, onUpload, onQuizzes }: { subjectId: number; onUpload: () => void; onQuizzes: () => void }) {
  const materials = useMaterials(subjectId)
  const remove = useDeleteMaterial(subjectId)
  const [deleting, setDeleting] = useState<Material | null>(null)

  const confirmDelete = () => {
    if (!deleting) return
    const name = deleting.filename
    remove.mutate(deleting.id, {
      onSuccess: () => { setDeleting(null); toast('success', 'File deleted', `${name} and its study tools were removed.`) },
      onError: () => toast('error', 'Couldn’t delete the file', 'Try again in a moment.'),
    })
  }

  return (
    <>
      <div className="tab-toolbar">
        <div>
          <h2>Course materials</h2>
          <p>{materials.data ? `${plural(materials.data.length, 'file')} · summaries and study tools stay linked to their source.` : 'Loading files…'}</p>
        </div>
        <Button icon="upload" onClick={onUpload}>Upload material</Button>
      </div>

      {materials.isPending && (
        <div className="materials-list" aria-busy="true" aria-label="Loading files">
          {[0, 1, 2].map(i => (
            <div className="workspace-material" key={i}><div className="material-row-main"><Skeleton className="skeleton-avatar" /><div className="skeleton-stack"><Skeleton /><Skeleton className="skeleton-label" /></div></div></div>
          ))}
        </div>
      )}
      {materials.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load this subject’s files.</p>
          <Button variant="secondary" onClick={() => materials.refetch()}>Try again</Button>
        </div>
      )}
      {materials.data?.length === 0 && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="upload" /></span>
          <h2>No files yet</h2>
          <p>Upload lecture notes, slides or recordings. XP will turn each one into a summary, flashcards and a quiz.</p>
          <Button icon="upload" onClick={onUpload}>Upload material</Button>
        </div>
      )}
      {!!materials.data?.length && (
        <div className="materials-list">
          {materials.data.map((m, i) => (
            <MaterialRow key={m.id} material={m} index={i} onDelete={() => setDeleting(m)} onQuizzes={onQuizzes} />
          ))}
        </div>
      )}

      <Modal open={!!deleting} onClose={() => !remove.isPending && setDeleting(null)} labelledBy="delete-title" small className="confirm-dialog">
        <span className="danger-icon"><Icon name="file" /></span>
        <h2 id="delete-title">Delete {deleting?.filename}?</h2>
        <p>Its summary, quiz, flashcards, and citations will also be removed. This can’t be undone.</p>
        <div className="modal-actions">
          <Button variant="secondary" onClick={() => setDeleting(null)} disabled={remove.isPending}>Cancel</Button>
          <Button variant="danger" onClick={confirmDelete} disabled={remove.isPending}>{remove.isPending ? 'Deleting…' : 'Delete file'}</Button>
        </div>
      </Modal>
    </>
  )
}
