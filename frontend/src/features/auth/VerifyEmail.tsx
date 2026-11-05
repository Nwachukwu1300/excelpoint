import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMe } from '../../lib/api'
import { Icon } from '../../ui/Icon'
import { Logo, buttonClass } from '../../ui/primitives'
import { post } from './AuthPage'
import '../../styles/auth.css'

/** Opened from the confirmation email. Works signed in or out: the signed link is the proof. */
export function VerifyEmail() {
  const { token = '' } = useParams()
  const signedIn = !!useMe().data
  const [result, setResult] = useState<'checking' | 'done' | string>('checking')
  const sent = useRef(false)

  useEffect(() => {
    if (sent.current) return // StrictMode runs effects twice in development
    sent.current = true
    post('/api/auth/verify-email/', { token }).then(r => setResult(r.ok ? 'done' : r.errors.__all__?.[0] ?? 'This link didn’t work. Sign in and ask for a new one.'))
  }, [token])

  return (
    <main className="auth-page">
      <Link className="auth-logo" to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
      <div className="auth-card" aria-busy={result === 'checking'}>
        <div>
          <h1>{result === 'checking' ? 'Confirming your email…' : result === 'done' ? 'Your email is confirmed' : 'We couldn’t confirm your email'}</h1>
          {result === 'done' && <p>Thanks. If you ever forget your password, we can now send you a link to reset it.</p>}
        </div>
        {result !== 'checking' && result !== 'done' && (
          <div className="auth-error" role="alert"><Icon name="close" size={15} /><span>{result}</span></div>
        )}
        {result !== 'checking' && (
          signedIn
            ? <a className={`${buttonClass()} auth-wide`} href="/app/">Open ExcelPoint</a>
            : <Link className={`${buttonClass()} auth-wide`} to="/login">Sign in</Link>
        )}
      </div>
    </main>
  )
}
