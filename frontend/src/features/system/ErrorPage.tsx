import { Link } from 'react-router'
import { Badge, Button, Logo, buttonClass } from '../../ui/primitives'

export function ErrorPage({ code }: { code: '404' | '500' }) {
  const missing = code === '404'
  return (
    <div className="error-page">
      <Logo />
      <div className="error-code" aria-hidden="true">{code}</div>
      <Badge tone={missing ? 'primary' : 'danger'}>{missing ? 'PAGE NOT FOUND' : 'SERVER ERROR'}</Badge>
      <h1>{missing ? 'This page isn’t here' : 'Something went wrong'}</h1>
      <p>
        {missing
          ? 'The page may have moved, or the link might be out of date.'
          : 'We couldn’t load this page. Your work is safe, please try again.'}
      </p>
      <div>
        {/* reloadDocument: after a crash, start from a clean page rather than the broken app state */}
        <Link to="/" className={buttonClass()} reloadDocument={!missing}>Back to Home</Link>
        {!missing && <Button variant="secondary" onClick={() => location.reload()}>Try again</Button>}
      </div>
    </div>
  )
}
