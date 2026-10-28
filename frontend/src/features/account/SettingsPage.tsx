import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type SyntheticEvent } from 'react'
import { Link } from 'react-router'
import { api, ApiError, useMe, type Me } from '../../lib/api'
import { useTheme, type Theme } from '../../lib/theme'
import { useOneAtATime } from '../../lib/useOneAtATime'
import { Icon, type IconName } from '../../ui/Icon'
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
          <p>Manage your profile and preferences.</p>
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
    </div>
  )
}
