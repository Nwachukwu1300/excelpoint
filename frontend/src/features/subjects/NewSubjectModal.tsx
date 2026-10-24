import { useState, type SyntheticEvent } from 'react'
import { useNavigate } from 'react-router'
import { ApiError, useMe } from '../../lib/api'
import { Modal } from '../../ui/Modal'
import { Button, IconButton } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import { useCreateSubject } from './api'

export function NewSubjectModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const me = useMe()
  const create = useCreateSubject()
  const navigate = useNavigate()

  const trimmed = name.trim()
  const duplicate = me.data?.subjects.some(s => s.name.toLowerCase() === trimmed.toLowerCase())
  const serverError = create.error instanceof ApiError
    ? ((create.error.data as { name?: string[] } | undefined)?.name?.[0] ?? create.error.message)
    : create.error ? 'Couldn’t create the subject. Try again.' : null
  const error = duplicate ? `A subject named ${trimmed} already exists.` : serverError

  const close = () => { setName(''); create.reset(); onClose() }
  const submit = (e: SyntheticEvent) => {
    e.preventDefault()
    if (!trimmed || duplicate) return
    create.mutate(trimmed, {
      onSuccess: subject => {
        close()
        toast('success', 'Subject created', `${subject.name} is ready for your first upload.`)
        navigate(`/subjects/${subject.id}`)
      },
    })
  }

  return (
    <Modal open={open} onClose={close} labelledBy="new-subject-title" small>
      <form onSubmit={submit}>
        <div className="modal-head">
          <div>
            <h2 id="new-subject-title">Create a new subject</h2>
            <p>Use a unique name you’ll recognise later.</p>
          </div>
          <IconButton icon="close" label="Close" onClick={close} />
        </div>
        <div className="form-field">
          <label htmlFor="subject-name">Subject name</label>
          <input
            id="subject-name"
            className={error ? 'text-input is-invalid' : 'text-input'}
            value={name}
            onChange={e => { setName(e.target.value); if (create.error) create.reset() }}
            placeholder="e.g. Human anatomy"
            maxLength={255}
            aria-invalid={!!error}
            aria-describedby={error ? 'subject-name-error' : undefined}
            autoFocus
          />
          {error && <span className="field-error" id="subject-name-error">{error}</span>}
        </div>
        <div className="modal-actions">
          <Button variant="secondary" onClick={close}>Cancel</Button>
          <Button type="submit" disabled={!trimmed || !!duplicate || create.isPending}>
            {create.isPending ? 'Creating…' : 'Create subject'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
