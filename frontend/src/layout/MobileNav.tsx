import { motion } from 'motion/react'
import { useLocation } from 'react-router'
import type { Me } from '../lib/api'
import { spring } from '../lib/motion'
import { Icon, type IconName } from '../ui/Icon'
import { NavLinkItem } from './NavLinkItem'

export function MobileNav({ me }: { me?: Me }) {
  const { pathname } = useLocation()
  const items: { icon: IconName; label: string; to?: string; href?: string; active: boolean; badge?: number }[] = [
    { icon: 'home', label: 'Home', to: '/', active: pathname === '/' },
    { icon: 'book', label: 'Subjects', to: '/subjects', active: pathname.startsWith('/subjects') },
    { icon: 'repeat', label: 'Review', to: '/review', active: pathname.startsWith('/review'), badge: me?.due_count },
    { icon: 'chart', label: 'Insights', to: '/insights', active: pathname.startsWith('/insights') },
    { icon: 'user', label: 'Account', to: '/settings', active: pathname.startsWith('/settings') || pathname.startsWith('/notifications') },
  ]
  return (
    <nav className="mobile-nav" aria-label="Mobile navigation">
      {items.map(item => (
        <NavLinkItem key={item.label} to={item.to} href={item.href} className={item.active ? 'is-active' : ''} aria-current={item.active ? 'page' : undefined}>
          {item.active && <motion.span layoutId="mobile-nav-active" className="nav-dot" transition={spring.morph} />}
          <Icon name={item.icon} />
          <span>{item.label}</span>
          {item.badge ? <small>{item.badge > 99 ? '99+' : item.badge}</small> : null}
        </NavLinkItem>
      ))}
    </nav>
  )
}
