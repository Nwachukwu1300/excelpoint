import type { ReactNode } from 'react'
import { Link } from 'react-router'

/** In-app routes use the router; old Django pages need a full page load. */
export function NavLinkItem({ to, href, children, ...props }: {
  to?: string
  href?: string
  className?: string
  title?: string
  'aria-current'?: 'page'
  children: ReactNode
}) {
  return to ? <Link to={to} {...props}>{children}</Link> : <a href={href} {...props}>{children}</a>
}
