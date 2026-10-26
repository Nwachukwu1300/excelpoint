import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type SyntheticEvent } from 'react'
import { useNavigate } from 'react-router'
import { api, ApiError, useMe } from '../../lib/api'
import { Icon } from '../../ui/Icon'
import { Button } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import '../../styles/account.css'

type Fields = { old_password: string; new_password1: string; new_password2: string }

export function ChangePassword() {
  const me = useMe()
  const setting = me.data ? !me.data.has_password : false // Google-only accounts set one instead
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<Fields>({ old_password: '', new_password1: '', new_password2: '' })
  const change = useMutation({
    mutationFn: (body: Partial<Fields>) => api('/api/me/password/', { method: 'POST', body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
      toast('success', setting ? 'Password set' : 'Password updated', 'You’re still signed in on this device.')
      navigate('/settings')
    },
  })
  const errors = change.error instanceof ApiError ? (change.error.data as Record<string, string[]> | undefined) ?? {} : {}

  const submit = (e: SyntheticEvent) => {
    e.preventDefault()
    const { old_password, ...rest } = form
    change.mutate(setting ? rest : form)
  }
  const field = (key: keyof Fields, label: string, autoComplete: string) => (
    <div className="form-field">
      <label htmlFor={key}>{label}</label>
      <input id={key} type="password" autoComplete={autoComplete} className={`text-input ${errors[key] ? 'is-invalid' : ''}`} value={form[key]}
        onChange={e => { setForm(f => ({ ...f, [key]: e.target.value })); change.reset() }}
        aria-invalid={!!errors[key]} aria-describedby={errors[key] ? `${key}-error` : undefined} required />
      {errors[key]?.map(msg => <span className="field-error" id={`${key}-error`} key={msg}>{msg}</span>)}
    </div>
  )

  return (
    <div className="page-content settings-page">
      <div className="page-intro">
        <div>
          <p className="overline">SECURITY</p>
          <h1>{setting ? 'Set a password' : 'Change password'}</h1>
          <p>{setting ? 'Add a password so you can sign in without Google.' : 'Choose a strong password you don’t use elsewhere.'}</p>
        </div>
      </div>
      <form className="settings-card password-card" onSubmit={submit}>
        {!setting && field('old_password', 'Current password', 'current-password')}
        {field('new_password1', 'New password', 'new-password')}
        {field('new_password2', 'Confirm new password', 'new-password')}
        <div className="password-requirements">
          <strong>Your password should:</strong>
          {/* The rules Django checks (AUTH_PASSWORD_VALIDATORS) */}
          <span><Icon name="check" size={13} /> Have at least 8 characters</span>
          <span><Icon name="check" size={13} /> Not be a common password or only numbers</span>
          <span><Icon name="check" size={13} /> Not be too similar to your name or email</span>
        </div>
        <Button type="submit" disabled={change.isPending}>
          {change.isPending ? 'Saving…' : setting ? 'Set password' : 'Update password'}
        </Button>
      </form>
    </div>
  )
}
