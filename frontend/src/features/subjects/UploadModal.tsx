import { useRef, useState } from 'react'
import { useMe } from '../../lib/api'
import { useOneAtATime } from '../../lib/useOneAtATime'
import { Icon } from '../../ui/Icon'
import { Modal } from '../../ui/Modal'
import { Button, IconButton } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import { ACCEPTED, checkFile, useUploadMaterial } from './api'

const sizeLabel = (bytes: number) => (bytes >= 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`)

export function UploadModal({ open, onClose, subjectId }: { open: boolean; onClose: () => void; subjectId: number }) {
  const me = useMe()
  const [target, setTarget] = useState(subjectId)
  const [file, setFile] = useState<File | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const uploadMaterial = useUploadMaterial()
  const once = useOneAtATime()

  const choose = (picked: File | undefined) => {
    if (!picked) return
    const issue = checkFile(picked)
    setProblem(issue)
    setFile(issue ? null : picked)
    uploadMaterial.reset()
  }
  const close = () => {
    if (uploadMaterial.isPending) return // don't drop an upload halfway
    setFile(null); setProblem(null); setTarget(subjectId); uploadMaterial.reset(); onClose()
  }
  const submit = () => {
    if (!file) return
    once(() => uploadMaterial.mutateAsync({ subjectId: target, file }).then(() => {
      const name = file.name
      setFile(null); setProblem(null); uploadMaterial.reset(); onClose()
      toast('success', `${name} uploaded`, 'XP is preparing its summary, flashcards and quiz. We’ll notify you when they’re ready.')
    }))
  }
  const error = problem ?? uploadMaterial.error?.message ?? null

  return (
    <Modal open={open} onClose={close} labelledBy="upload-title">
      <div className="modal-head">
        <div>
          <h2 id="upload-title">Add study material</h2>
          <p>XP will create a summary, flashcards, and a quiz.</p>
        </div>
        <IconButton icon="close" label="Close" onClick={close} />
      </div>
      <div className="form-field">
        <label htmlFor="upload-subject">Subject</label>
        <div className="select-wrap">
          <select id="upload-subject" value={target} onChange={e => setTarget(Number(e.target.value))} disabled={uploadMaterial.isPending}>
            {me.data?.subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <Icon name="chevronDown" size={15} />
        </div>
      </div>
      <input
        ref={input}
        type="file"
        hidden
        accept={ACCEPTED.map(ext => `.${ext}`).join(',')}
        onChange={e => { choose(e.target.files?.[0]); e.target.value = '' }}
      />
      <button
        type="button"
        className={`dropzone ${dragging ? 'is-dragging' : ''}`}
        onClick={() => !uploadMaterial.isPending && input.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); if (!uploadMaterial.isPending) choose(e.dataTransfer.files[0]) }}
        aria-describedby={error ? 'upload-error' : undefined}
      >
        {uploadMaterial.isPending ? (
          <>
            <span className="upload-icon"><Icon name="sparkles" /></span>
            <strong>Uploading {file?.name}…</strong>
            <span>Keep this open until the upload finishes.</span>
          </>
        ) : file ? (
          <>
            <span className="upload-icon success"><Icon name="check" /></span>
            <strong>{file.name}</strong>
            <span>{sizeLabel(file.size)} · Ready to upload · Choose a different file</span>
          </>
        ) : (
          <>
            <span className="upload-icon"><Icon name="upload" /></span>
            <strong>Drag a file here, or click to choose one</strong>
            <span>PDF or Word (.docx) · up to 100 MB</span>
          </>
        )}
      </button>
      {error && (
        <div className="upload-file-error" id="upload-error" role="alert">
          <Icon name="close" size={14} />
          <span>{error}</span>
        </div>
      )}
      <div className="modal-note">
        <Icon name="lock" size={15} />
        <span>Your materials are private. XP never uses information outside your uploads.</span>
      </div>
      <div className="modal-actions">
        <Button variant="secondary" onClick={close} disabled={uploadMaterial.isPending}>Cancel</Button>
        <Button icon="upload" disabled={!file || uploadMaterial.isPending} onClick={submit}>
          {uploadMaterial.isPending ? 'Uploading…' : 'Upload material'}
        </Button>
      </div>
    </Modal>
  )
}
