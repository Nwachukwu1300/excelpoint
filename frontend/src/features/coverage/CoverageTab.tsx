import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ApiError } from '../../lib/api'
import { plural } from '../../lib/format'
import { Icon } from '../../ui/Icon'
import { Modal } from '../../ui/Modal'
import { ProgressRing } from '../../ui/ProgressRing'
import { Badge, Button, ProgressBar, Skeleton, buttonClass } from '../../ui/primitives'
import { startSession } from '../explain/api'
import { LOOK, ORDER, startSectionQuiz, useCoverage, useSection, type Coverage, type FileCoverage, type Status } from './api'
import '../../styles/coverage.css'

export function StatusChip({ status }: { status: Status }) {
  const look = LOOK[status]
  return <Badge tone={look.tone}>{look.icon && <Icon name={look.icon} size={13} />}{look.label}</Badge>
}

/** One small square per section: its shape (dashed, striped, filled, faded) differs as well as its colour. */
function Strip({ file }: { file: FileCoverage }) {
  return (
    <span className="coverage-strip" aria-hidden="true">
      {file.sections.map(s => <i key={s.id} className={`is-${s.status}`} />)}
    </span>
  )
}

/** "You've studied 62% of Biology." with the sentence; also shown above every tab of the subject. */
export function headline(data: Coverage) {
  return `You’ve studied ${data.percent}% of ${data.subject.name}.`
}

function FileRow({ file, open, onToggle, onSection }: { file: FileCoverage; open: boolean; onToggle: () => void; onSection: (id: number) => void }) {
  if (file.state !== 'ready') {
    const text = file.state === 'failed' ? `Couldn’t read this file. ${file.error}`.trim()
      : file.state === 'processing' ? 'Reading this file… Its parts appear here when it’s ready.' : 'Building the map of this file…'
    return (
      <li className={`coverage-file is-${file.state}`}>
        <div className="coverage-file-head is-static">
          <Icon name="file" />
          <div><strong>{file.name}</strong><span>{text}</span></div>
        </div>
        {file.state !== 'failed' && <ProgressBar label={text} />}
      </li>
    )
  }
  return (
    <li className="coverage-file">
      <button type="button" className="coverage-file-head" aria-expanded={open} onClick={onToggle}>
        <Icon name="file" />
        <div>
          <strong>{file.name}</strong>
          <span>{file.studied} of {plural(file.sections.length, 'section')} studied</span>
          <Strip file={file} />
        </div>
        <Icon name={open ? 'chevronDown' : 'chevronRight'} size={16} />
      </button>
      {open && (
        <ul className="coverage-sections">
          {file.sections.map(s => (
            <li key={s.id}>
              <button type="button" onClick={() => onSection(s.id)}>
                <span><strong>{s.title}</strong>{s.range && s.range !== s.title && <small>{s.range}</small>}</span>
                <StatusChip status={s.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

export function CoverageTab({ subjectId, onUpload }: { subjectId: number; onUpload: () => void }) {
  const coverage = useCoverage(subjectId)
  const [params, setParams] = useSearchParams()
  const sectionId = Number(params.get('section')) || null
  const setSection = (id: number | null) => {
    const next = new URLSearchParams(params)
    if (id) next.set('section', String(id))
    else next.delete('section')
    setParams(next, { replace: !id })
  }
  const data = coverage.data
  const many = (data?.files.length ?? 0) > 4
  const [toggled, setToggled] = useState<Record<number, boolean>>({})
  const isOpen = (id: number) => toggled[id] ?? !many // small subjects open every file; big ones start closed

  return (
    <>
      {coverage.isPending && <div className="skeleton-stack"><Skeleton /><Skeleton /><Skeleton /></div>}
      {coverage.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load the coverage map.</p>
          <Button variant="secondary" onClick={() => coverage.refetch()}>Try again</Button>
        </div>
      )}
      {data?.state === 'empty' && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="layers" /></span>
          <h2>Upload notes first</h2>
          <p>The coverage map shows which parts of your files you’ve studied. Upload a file to see it.</p>
          <Button icon="upload" onClick={onUpload}>Upload file</Button>
        </div>
      )}
      {data?.state === 'ready' && (
        <>
          <section className="coverage-hero" aria-label="Coverage">
            <ProgressRing value={data.percent} label="studied" />
            <div>
              <h2>{headline(data)}</h2>
              <p>{data.sentence || 'Your map appears here once a file is ready.'}</p>
              <ul className="coverage-legend" aria-label="Sections by status">
                {ORDER.map(s => (
                  <li key={s}><i className={`coverage-key is-${s}`} aria-hidden="true">{LOOK[s].icon && <Icon name={LOOK[s].icon!} size={11} />}</i>{LOOK[s].label} <b>{data.counts[s]}</b></li>
                ))}
              </ul>
            </div>
          </section>
          <ul className="coverage-files">
            {data.files.map(f => (
              <FileRow key={f.id} file={f} open={isOpen(f.id)} onToggle={() => setToggled(t => ({ ...t, [f.id]: !isOpen(f.id) }))} onSection={setSection} />
            ))}
          </ul>
        </>
      )}
      <SectionSheet id={sectionId} onClose={() => setSection(null)} />
    </>
  )
}

const WHY: Record<Status, string> = {
  not_studied: 'Why is this not studied?', shaky: 'Why is this shaky?', solid: 'Why is this solid?', fading: 'Why is this fading?',
}

function SectionSheet({ id, onClose }: { id: number | null; onClose: () => void }) {
  const section = useSection(id)
  const navigate = useNavigate()
  const [why, setWhy] = useState(false)
  const [whole, setWhole] = useState(false)
  const [busy, setBusy] = useState<'quiz' | 'explain' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const s = section.data

  async function go(kind: 'quiz' | 'explain') {
    if (!s) return
    setBusy(kind)
    setError(null)
    try {
      if (kind === 'quiz') {
        const attempt = await startSectionQuiz(s.id)
        navigate(`/quiz-attempts/${attempt.id}`)
      } else {
        const session = await startSession(s.subject_id, { section_id: s.id })
        if ('id' in session) navigate(`/subjects/${s.subject_id}/explain/${session.id}`)
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'That didn’t start. Try again in a moment.')
      setBusy(null)
    }
  }

  const text = s?.passages.map(p => p.content).join(' ') ?? ''
  return (
    <Modal open={!!id} onClose={onClose} labelledBy="section-title" className="section-sheet">
      {section.isPending && <div className="skeleton-stack"><Skeleton /><Skeleton /><Skeleton /></div>}
      {section.isError && <p className="inline-note" role="alert">{section.error instanceof ApiError ? section.error.message : 'We couldn’t load this part.'}</p>}
      {s && (
        <>
          <div className="section-sheet-head">
            <StatusChip status={s.status} />
            <h2 id="section-title">{s.title}</h2>
            <p>{[s.range !== s.title ? s.range : null, s.file.name].filter(Boolean).join(' · ')}</p>
          </div>
          <button type="button" className="section-why" aria-expanded={why} onClick={() => setWhy(w => !w)}>{WHY[s.status]}</button>
          {why && <p className="section-reason">{s.reason}</p>}
          <figure className="answer-evidence section-text">
            <figcaption><Icon name="file" size={15} /><span>From <strong>{s.file.name}</strong></span></figcaption>
            <blockquote className={whole ? '' : 'is-clamped'}>{text}</blockquote>
            {text.length > 280 && (
              <div className="evidence-actions"><button type="button" aria-expanded={whole} onClick={() => setWhole(w => !w)}>{whole ? 'Show less' : 'Show the whole section'}</button></div>
            )}
          </figure>
          {error && <p className="section-error" role="alert">{error}</p>}
          <div className="section-actions">
            {s.cards > 0 && (
              <Link className={buttonClass('secondary')} to={`/review?section=${s.id}`}><Icon name="repeat" />Study {plural(s.cards, 'flashcard')}</Link>
            )}
            <Button variant="secondary" icon="layers" disabled={!!busy} onClick={() => go('quiz')}>{busy === 'quiz' ? 'Starting quiz…' : 'Quiz this section'}</Button>
            <Button variant="ai" icon="mic" disabled={!!busy} onClick={() => go('explain')}>{busy === 'explain' ? 'Starting…' : 'Explain it to XP'}</Button>
          </div>
        </>
      )}
    </Modal>
  )
}

/** The headline above a subject's tabs: the % and the sentence, with a way into the map. */
export function CoverageHeadline({ subjectId, onOpen }: { subjectId: number; onOpen: () => void }) {
  const coverage = useCoverage(subjectId)
  const data = coverage.data
  if (!data || data.state === 'empty' || !data.sentence) return null
  return (
    <div className="coverage-headline">
      <p><strong>{headline(data)}</strong> {data.sentence}</p>
      <button type="button" onClick={onOpen}>See the map <Icon name="arrow" size={14} /></button>
    </div>
  )
}
