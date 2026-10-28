import { useEffect, useState, type SyntheticEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import { csrfToken, googleSignIn, useMe } from '../../lib/api'
import { Icon } from '../../ui/Icon'
import { Button, Logo } from '../../ui/primitives'
import '../../styles/auth.css'

type Errors = Record<string, string[]>

/** Plain fetch: these endpoints are Django views (CSRF-protected for signed-out visitors too). */
async function post(path: string, body: object): Promise<{ ok: true; next: string } | { ok: false; errors: Errors }> {
  const r = await fetch(path, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-CSRFToken': csrfToken() },
    body: JSON.stringify(body),
  })
  const data = await r.json().catch(() => ({}))
  if (r.ok) return { ok: true, next: data.next ?? '/app/' }
  if (r.status === 403) return { ok: false, errors: { __all__: ['Your session expired. Refresh the page and try again.'] } }
  return { ok: false, errors: data.detail ? { __all__: [data.detail] } : data }
}

/** Only same-site paths; the URL parser catches tricks like `/\evil.com` that browsers read as `//evil.com`. */
function safeNext(next?: string) {
  try {
    const u = new URL(next ?? '', location.origin)
    if (next && u.origin === location.origin) return u.pathname + u.search + u.hash
  } catch { /* not a URL: fall through */ }
  return '/app/'
}

export function AuthPage({ mode }: { mode: 'signin' | 'register' }) {
  const register = mode === 'register'
  const [params] = useSearchParams()
  const next = params.get('next') ?? undefined
  const me = useMe() // signed in already? go straight in
  useEffect(() => { if (me.data) location.replace(safeNext(next)) }, [me.data, next])

  const [form, setForm] = useState({ username: '', email: '', password1: '', password2: '' })
  const [errors, setErrors] = useState<Errors>(params.get('error') === 'google' ? { __all__: ['Google sign-in didn’t work. Try again, or use your username and password.'] } : {})
  const [busy, setBusy] = useState(false)

  const submit = async (e: SyntheticEvent) => {
    e.preventDefault()
    setBusy(true)
    const result = register
      ? await post('/api/auth/register/', form)
      : await post('/api/auth/login/', { username: form.username, password: form.password1, next })
    if (result.ok) { location.assign(result.next); return } // full load: start the app fresh with the new session
    setErrors(result.errors)
    setBusy(false)
  }
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => { setForm(f => ({ ...f, [key]: e.target.value })); setErrors({}) }
  const field = (key: keyof typeof form, label: string, type: string, autoComplete: string, placeholder: string, hint?: string) => (
    <div className="form-field">
      <label htmlFor={`auth-${key}`}>{label}</label>
      <input id={`auth-${key}`} className={`text-input ${errors[key] ? 'is-invalid' : ''}`} type={type} autoComplete={autoComplete}
        placeholder={placeholder} value={form[key]} onChange={set(key)} required aria-invalid={!!errors[key]}
        aria-describedby={[hint && `auth-${key}-hint`, errors[key] && `auth-${key}-error`].filter(Boolean).join(' ') || undefined} />
      {hint && <span className="field-hint" id={`auth-${key}-hint`}>{hint}</span>}
      {errors[key]?.map(m => <span className="field-error" id={`auth-${key}-error`} key={m}>{m}</span>)}
    </div>
  )

  return (
    <div className="auth-page">
      <Link className="auth-logo" to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
      <form className="auth-card" onSubmit={submit}>
        <div>
          <h1>{register ? 'Create your account' : 'Welcome back'}</h1>
          <p>{register ? 'Turn your class notes into summaries, quizzes and flashcards.' : 'Sign in to continue studying.'}</p>
        </div>
        {googleSignIn(me) && (
          <>
            <a className="button button--secondary google-button" href="/users/google/login/"><span className="google-mark" aria-hidden="true">G</span>Continue with Google</a>
            <div className="auth-divider"><span>or continue with {register ? 'email' : 'your username'}</span></div>
          </>
        )}
        {errors.__all__ && (
          <div className="auth-error" role="alert"><Icon name="close" size={15} /><span>{errors.__all__[0]}</span></div>
        )}
        {field('username', 'Username', 'text', 'username', 'alexmorgan')}
        {register && field('email', 'Email', 'email', 'email', 'alex@example.com', 'Only for your account. We don’t send marketing email.')}
        {field('password1', 'Password', 'password', register ? 'new-password' : 'current-password', register ? 'At least 8 characters' : 'Your password',
          register ? 'At least 8 characters, not only numbers, and not a common password.' : undefined)}
        {register && field('password2', 'Confirm password', 'password', 'new-password', 'Repeat your password')}
        <Button type="submit" className="full-width" disabled={busy}>
          {busy ? (register ? 'Creating account…' : 'Signing in…') : register ? 'Create account' : 'Sign in'}
        </Button>
        {register && <p className="auth-privacy">Your files and questions stay private to you. <Link to="/privacy">Read how we handle your data</Link></p>}
        <p className="auth-switch">
          {register ? 'Already have an account?' : 'New to ExcelPoint?'}{' '}
          <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create an account'}</Link>
        </p>
      </form>
    </div>
  )
}
