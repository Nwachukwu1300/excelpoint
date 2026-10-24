import { motion } from 'motion/react'
import { Link, useParams, useSearchParams } from 'react-router'
import { plural, timeAgo } from '../../lib/format'
import { spring } from '../../lib/motion'
import { oldPages } from '../../layout/nav'
import { Icon } from '../../ui/Icon'
import { Skeleton, buttonClass } from '../../ui/primitives'
import { useSubjects } from './api'
import { FlashcardsTab } from './FlashcardsTab'
import { MaterialsTab } from './MaterialsTab'
import { QuizzesTab } from './QuizzesTab'
import { UploadModal } from './UploadModal'
import '../../styles/subjects.css'

const TABS = ['materials', 'quizzes', 'flashcards'] as const
type Tab = (typeof TABS)[number]

export function SubjectWorkspace() {
  const id = Number(useParams().subjectId)
  const subjects = useSubjects()
  const [params, setParams] = useSearchParams()
  const tab: Tab = TABS.find(t => t === params.get('tab')) ?? 'materials'
  const uploading = params.get('upload') === '1'

  // Tab and upload live in the URL so links (e.g. Home's "Upload") can open them directly.
  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v === null) next.delete(k)
      else next.set(k, v)
    }
    setParams(next, { replace: true })
  }
  const setTab = (t: Tab) => update({ tab: t === 'materials' ? null : t })
  const setUploading = (on: boolean) => update({ upload: on ? '1' : null })

  const subject = subjects.data?.find(s => s.id === id)
  if (subjects.isSuccess && !subject) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <span className="empty-icon"><Icon name="book" /></span>
          <h2>Subject not found</h2>
          <p>It may have been deleted, or the link is out of date.</p>
          <Link className={buttonClass('secondary')} to="/subjects">Back to subjects</Link>
        </div>
      </div>
    )
  }

  const tabButton = (t: Tab, label: string, count?: number) => (
    <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? 'is-active' : ''} onClick={() => setTab(t)}>
      {label}
      {count ? <small>{count}</small> : null}
      {tab === t && <motion.span layoutId="workspace-tab" className="tab-underline" transition={spring.morph} />}
    </button>
  )

  return (
    <div className="page-content workspace-page">
      <div className="workspace-header">
        <div>
          <div className="workspace-breadcrumb">
            <Link to="/subjects">Subjects</Link> <Icon name="chevronRight" size={13} /> {subject?.name}
          </div>
          {subject ? (
            <>
              <h1>{subject.name}</h1>
              <p>{plural(subject.materials_count, 'material')} · Updated {timeAgo(subject.updated_at)}</p>
            </>
          ) : (
            <div className="skeleton-stack"><Skeleton className="skeleton-value" /><Skeleton className="skeleton-label" /></div>
          )}
        </div>
        <div className="workspace-actions">
          <button type="button" className={buttonClass('secondary')} onClick={() => setUploading(true)}><Icon name="upload" />Upload material</button>
          {subject?.due_count
            ? <a className={buttonClass('secondary')} href={oldPages.review(id)}><Icon name="repeat" />Review {subject.due_count} due</a>
            : <button type="button" className={buttonClass('secondary')} disabled><Icon name="repeat" />Nothing due</button>}
          <a className={buttonClass('ai')} href={oldPages.chat(id)}><Icon name="sparkles" />Ask XP</a>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Subject sections">
        {tabButton('materials', 'Materials')}
        <a role="tab" aria-selected={false} href={oldPages.chat(id)}>Chat</a>
        {tabButton('quizzes', 'Quizzes')}
        {tabButton('flashcards', 'Flashcards', subject?.due_count)}
      </div>

      <motion.section
        key={tab}
        className="workspace-tab"
        role="tabpanel"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
      >
        {tab === 'materials' && <MaterialsTab subjectId={id} onUpload={() => setUploading(true)} onQuizzes={() => setTab('quizzes')} />}
        {tab === 'quizzes' && <QuizzesTab subjectId={id} />}
        {tab === 'flashcards' && <FlashcardsTab subjectId={id} dueCount={subject?.due_count ?? 0} />}
      </motion.section>

      <UploadModal open={uploading} onClose={() => setUploading(false)} subjectId={id} />
    </div>
  )
}
