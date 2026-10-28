import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type SyntheticEvent } from 'react'
import { Link } from 'react-router'
import { api, ApiError, useMe, type Me } from '../../lib/api'
import { useTheme, type Theme } from '../../lib/theme'
import { useOneAtATime } from '../../lib/useOneAtATime'
import { Icon, type IconName } from '../../ui/Icon'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { Button, Skeleton } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import '../../styles/account.css'

type Form = { first_name: string; last_name: string; email: string; education_level: string }
const THEMES: { value: Theme; label: string; note: string; icon: IconName }[] = [
  { value: 'light', label: 'Light', note: 'Light theme', icon: 'sun' },
  { value: 'dark', label: 'Dark', note: 'Dark theme', icon: 'moon' },
  { value: 'system', label: 'System', note: 'Match this device', icon: 'settings' },
]

export function SettingsPage() {
  const me = useMe()
  const queryClient = useQueryClient()
  const { theme, setTheme } = useTheme()
  const [form, setForm] = useState<Form | null>(null)
  useEffect(() => {
    if (me.data && !form) setForm({ first_name: me.data.first_name, last_name: me.data.last_name, email: me.data.email, education_level: me.data.education_level })
  }, [me.data, form])

  const save = useMutation({
    mutationFn: (body: Form) => api<Me>('/api/me/', { method: 'PATCH', body }),
    onSuccess: data => {
      queryClient.setQueryData(['me'], data)
      toast('success', 'Changes saved', 'Your profile and preferences are up to date.')
    },
  })
  const errors = save.error instanceof ApiError ? (save.error.data as Record<string, string[]> | undefined) ?? {} : {}
  const set = (key: keyof Form) => (e: { target: { value: string } }) => { setForm(f => f && { ...f, [key]: e.target.value }); save.reset() }
  const once = useOneAtATime()
  const submit = (e: SyntheticEvent) => { e.preventDefault(); if (form) once(() => save.mutateAsync(form)) }

  if (!form || !me.data) {
    return <div className="page-content settings-page" aria-busy="true"><div className="settings-card"><div className="skeleton-stack"><Skeleton className="skeleton-label" /><Skeleton /><Skeleton /></div></div></div>
  }
  const field = (key: keyof Form, label: string, type = 'text', full = false) => (
    <div className={`form-field ${full ? 'full-field' : ''}`}>
      <label htmlFor={`settings-${key}`}>{label}</label>
      <input id={`settings-${key}`} className={`text-input ${errors[key] ? 'is-invalid' : ''}`} type={type} value={form[key]} onChange={set(key)}
        aria-invalid={!!errors[key]} aria-describedby={errors[key] ? `settings-${key}-error` : undefined} />
      {errors[key] && <span className="field-error" id={`settings-${key}-error`}>{errors[key]![0]}</span>}
    </div>
  )

  return (
    <div className="page-content settings-page">
      <div className="page-intro">
        <div>
          <p className="overline">ACCOUNT</p>
          <h1>Settings</h1>
          <p>Manage your profile and preferences. <Link to="/privacy">How we handle your data</Link></p>
        </div>
      </div>
      <form className="settings-card" onSubmit={submit}>
        <div className="settings-section-head">
          <h2>Personal information</h2>
          <p>Used to personalise your ExcelPoint experience.</p>
        </div>
        <div className="form-grid">
          {field('first_name', 'First name')}
          {field('last_name', 'Last name')}
          {field('email', 'Email', 'email', true)}
          <div className="form-field full-field">
            <label htmlFor="settings-education">Level of education</label>
            <div className="select-wrap">
              <select id="settings-education" value={form.education_level} onChange={set('education_level')}>
                <option value="">— Select —</option>
                {me.data.education_choices.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              <Icon name="chevronDown" size={15} />
            </div>
            {errors.education_level && <span className="field-error">{errors.education_level[0]}</span>}
          </div>
        </div>
        <div className="settings-divider" />
        <div className="settings-section-head">
          <h2>Appearance</h2>
          <p>Choose how ExcelPoint looks on this device. This applies straight away.</p>
        </div>
        <div className="theme-options" role="radiogroup" aria-label="Theme">
          {THEMES.map(t => (
            <button type="button" role="radio" aria-checked={theme === t.value} key={t.value} className={theme === t.value ? 'is-active' : ''} onClick={() => setTheme(t.value)}>
              <Icon name={t.icon} />
              <strong>{t.label}</strong>
              <span>{t.note}</span>
            </button>
          ))}
        </div>
        <div className="settings-divider" />
        <Link className="password-link" to="/settings/password">
          <span className="empty-icon"><Icon name="lock" /></span>
          <div>
            <strong>{me.data.has_password ? 'Change password' : 'Set a password'}</strong>
            <p>{me.data.has_password ? 'Update the password you use to sign in.' : 'Add a password so you can sign in without Google.'}</p>
          </div>
          <Icon name="chevronRight" />
        </Link>
        <div className="settings-save">
          {save.isError && !Object.keys(errors).some(k => k in form) && (
            <span className="field-error" role="alert">Your changes weren’t saved. Check your connection and try again.</span>
          )}
          <Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save changes'}</Button>
        </div>
      </form>
      <DeleteAccount hasPassword={me.data.has_password} username={me.data.username} />
    </div>
  )
}

function DeleteAccount({ hasPassword, username }: { hasPassword: boolean; username: string }) {
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState('')
  const once = useOneAtATime()
  const remove = useMutation({ mutationFn: () => api('/api/me/delete/', { method: 'POST', body: { confirm } }) })
  const error = remove.error instanceof ApiError
    ? (remove.error.data as { confirm?: string[] } | null)?.confirm?.[0] ?? 'Your account wasn’t deleted. Try again.'
    : null
  const cancel = () => { setOpen(false); setConfirm(''); remove.reset() }
  return (
    <section className="settings-card danger-zone" aria-labelledby="delete-account-title">
      <div className="settings-section-head">
        <h2 id="delete-account-title">Delete account</h2>
        <p>Removes your account and everything in it: files, summaries, flashcards, quizzes and XP conversations.</p>
      </div>
      <Button variant="danger" onClick={() => setOpen(true)}>Delete my account</Button>
      <ConfirmDialog open={open} title="Delete your account?" confirmLabel="Delete account" icon="user" busy={remove.isPending}
        onCancel={cancel} onConfirm={() => confirm && once(() => remove.mutateAsync().then(() => location.assign('/app/welcome?deleted=1')), { final: true })}>
        <p>Everything in ExcelPoint that belongs to you will be removed. This can’t be undone.</p>
        <div className="form-field">
          <label htmlFor="delete-confirm">{hasPassword ? 'Enter your password to confirm' : `Type your username (${username}) to confirm`}</label>
          <input id="delete-confirm" className={`text-input ${error ? 'is-invalid' : ''}`} type={hasPassword ? 'password' : 'text'}
            autoComplete={hasPassword ? 'current-password' : 'off'} value={confirm} onChange={e => { setConfirm(e.target.value); remove.reset() }}
            aria-invalid={!!error} aria-describedby={error ? 'delete-confirm-error' : undefined} />
          {error && <span className="field-error" id="delete-confirm-error" role="alert">{error}</span>}
        </div>
      </ConfirmDialog>
    </section>
  )
}
