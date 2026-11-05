import { useState } from 'react'
import { Link } from 'react-router'
import { api, ApiError, type Me } from '../lib/api'
import { useOneAtATime } from '../lib/useOneAtATime'
import { Icon } from '../ui/Icon'
import { toast } from '../ui/Toast'

const HIDDEN_KEY = 'xp-email-banner-hidden'
const readHidden = () => { try { return sessionStorage.getItem(HIDDEN_KEY) === '1' } catch { return false } }

/** Asks a student to confirm their email. They can study meanwhile; it only matters for password reset. */
export function EmailBanner({ me }: { me: Me }) {
  const [hidden, setHidden] = useState(readHidden)
  const once = useOneAtATime()
  if (me.email_verified || hidden) return null

  const hide = () => {
    try { sessionStorage.setItem(HIDDEN_KEY, '1') } catch { /* hidden for this page only */ }
    setHidden(true)
  }
  const resend = () => once(() => api<{ email: string }>('/api/me/confirm-email/', { method: 'POST' }).then(
    r => toast('success', 'Link sent', `Check ${r.email}, and your spam folder too.`),
    e => toast('error', 'Couldn’t send the link', e instanceof ApiError ? e.message : 'Try again in a moment.'),
  ))

  return (
    <section className="email-banner" aria-label="Email confirmation">
      <Icon name="bell" size={16} />
      {me.email
        ? <p role="status"><strong>Confirm your email.</strong> We sent a link to {me.email}. It lets you reset your password if you forget it.</p>
        : <p role="status"><strong>Add your email.</strong> Without one, you can’t reset your password if you forget it.</p>}
      <div>
        {me.email && <button type="button" onClick={resend}>Send again</button>}
        <Link to="/settings">{me.email ? 'Change email' : 'Add email'}</Link>
        <button type="button" className="email-banner-close" aria-label="Hide for now" onClick={hide}><Icon name="close" size={15} /></button>
      </div>
    </section>
  )
}
