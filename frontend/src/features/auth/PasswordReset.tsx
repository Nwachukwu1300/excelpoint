import { useState, type SyntheticEvent } from 'react'
import { Link, useParams } from 'react-router'
import { Icon } from '../../ui/Icon'
import { Button, Logo } from '../../ui/primitives'
import { post } from './AuthPage'
import '../../styles/auth.css'

type Errors = Record<string, string[]>

function Card({ title, intro, children }: { title: string; intro: string; children: React.ReactNode }) {
  return (
    <div className="auth-page">
      <Link className="auth-logo" to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
      <div className="auth-card">
        <div>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
        {children}
        <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
      </div>
    </div>
  )
}

const errorBox = (errors: Errors) => errors.__all__ && (
  <div className="auth-error" role="alert"><Icon name="close" size={15} /><span>{errors.__all__[0]}</span></div>
)

/** Step 1: ask for a link by email. The answer is the same whether or not the email has an account. */
export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState<string | null>(null)
  const [errors, setErrors] = useState<Errors>({})
  const [busy, setBusy] = useState(false)
  const submit = async (e: SyntheticEvent) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    const result = await post('/api/auth/password-reset/', { email })
    setBusy(false)
    if (result.ok) setSent(email)
    else setErrors(result.errors)
  }
  if (sent) {
    return (
      <Card title="Check your email" intro={`If an account uses ${sent}, we’ve sent it a link to set a new password. The link works for 2 hours.`}>
        <p className="auth-privacy">No email after a few minutes? Check your spam folder, or try again with the email you signed up with.</p>
      </Card>
    )
  }
  return (
    <Card title="Forgot your password?" intro="Enter the email you signed up with, and we’ll send you a link to set a new password.">
      <form onSubmit={submit}>
        {errorBox(errors)}
        <div className="form-field">
          <label htmlFor="reset-email">Email</label>
          <input id="reset-email" className="text-input" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />
        </div>
        <Button type="submit" className="full-width" disabled={busy}>{busy ? 'Sending…' : 'Send me a link'}</Button>
      </form>
    </Card>
  )
}

/** Step 2: the link from the email. A new password signs you straight in. */
export function ResetPassword() {
  const { uid = '', token = '' } = useParams()
  const [form, setForm] = useState({ new_password1: '', new_password2: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [busy, setBusy] = useState(false)
  const submit = async (e: SyntheticEvent) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    const result = await post('/api/auth/password-reset/confirm/', { uid, token, ...form })
    if (result.ok) { location.assign(result.next); return }
    setErrors(result.errors)
    setBusy(false)
  }
  const field = (key: keyof typeof form, label: string, hint?: string) => (
    <div className="form-field">
      <label htmlFor={`reset-${key}`}>{label}</label>
      <input id={`reset-${key}`} className={`text-input ${errors[key] ? 'is-invalid' : ''}`} type="password" autoComplete="new-password" required
        value={form[key]} onChange={e => { setForm(f => ({ ...f, [key]: e.target.value })); setErrors({}) }}
        aria-invalid={!!errors[key]} aria-describedby={[hint && `reset-${key}-hint`, errors[key] && `reset-${key}-error`].filter(Boolean).join(' ') || undefined} />
      {hint && <span className="field-hint" id={`reset-${key}-hint`}>{hint}</span>}
      {errors[key]?.map(m => <span className="field-error" id={`reset-${key}-error`} key={m}>{m}</span>)}
    </div>
  )
  const expired = errors.__all__?.[0]?.includes('expired')
  return (
    <Card title="Set a new password" intro="Choose a new password for your ExcelPoint account.">
      <form onSubmit={submit}>
        {errorBox(errors)}
        {expired && <p className="auth-privacy"><Link to="/forgot-password">Send me a new link</Link></p>}
        {field('new_password1', 'New password', 'At least 8 characters, not only numbers, and not a common password.')}
        {field('new_password2', 'Confirm new password')}
        <Button type="submit" className="full-width" disabled={busy}>{busy ? 'Saving…' : 'Save and sign in'}</Button>
      </form>
    </Card>
  )
}
