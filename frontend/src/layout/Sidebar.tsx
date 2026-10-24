import { motion } from 'motion/react'
import { useLocation } from 'react-router'
import { displayName, initials, type Me } from '../lib/api'
import { spring } from '../lib/motion'
import { Icon, type IconName } from '../ui/Icon'
import { Avatar, Badge, IconButton, Logo, Skeleton } from '../ui/primitives'
import { NavLinkItem } from './NavLinkItem'
import { oldPages, reviewHref } from './nav'

type Item = { icon: IconName; label: string; to?: string; href?: string; badge?: number; active: boolean }

function NavItem({ item, collapsed }: { item: Item; collapsed: boolean }) {
  return (
    <NavLinkItem
      to={item.to}
      href={item.href}
      className={`nav-item ${item.active ? 'is-active' : ''}`}
      title={collapsed ? item.label : undefined}
      aria-current={item.active ? 'page' : undefined}
    >
      {item.active && <motion.div layoutId="nav-active" className="nav-active" transition={spring.morph} />}
      <Icon name={item.icon} />
      {!collapsed && <span>{item.label}</span>}
      {!collapsed && item.badge ? <span className="nav-badge">{item.badge}</span> : null}
    </NavLinkItem>
  )
}

export function Sidebar({ me, collapsed, onToggle }: { me?: Me; collapsed: boolean; onToggle: () => void }) {
  const { pathname } = useLocation()
  const items: Item[] = [
    { icon: 'home', label: 'Home', to: '/', active: pathname === '/' },
    { icon: 'book', label: 'Subjects', href: oldPages.subjects, active: pathname.startsWith('/subjects') },
    { icon: 'repeat', label: 'Review', href: reviewHref(me), badge: me?.due_count, active: pathname.startsWith('/review') },
    { icon: 'chart', label: 'Insights', href: oldPages.insights, active: pathname.startsWith('/insights') },
  ]
  const name = me ? displayName(me) : ''

  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`}>
      <div className="sidebar-top">
        {collapsed
          ? <button type="button" className="logo-button" aria-label="Expand sidebar" title="Expand sidebar" onClick={onToggle}><Logo compact /></button>
          : <Logo />}
        <IconButton icon="panel" label="Collapse sidebar" onClick={onToggle} />
      </div>
      <nav className="main-nav" aria-label="Primary navigation">
        <NavItem item={items[0]!} collapsed={collapsed} />
        <NavItem item={items[1]!} collapsed={collapsed} />
        {!collapsed && me && (
          <div className="subject-nav">
            {me.subjects.map(s => (
              <a key={s.id} href={oldPages.subject(s.id)}>
                <span>{s.name}</span>
                <small>{s.due_count}</small>
              </a>
            ))}
            <a className="new-subject" href={oldPages.subjects}>
              <Icon name="plus" size={14} />
              <span>New subject</span>
            </a>
          </div>
        )}
        <NavItem item={items[2]!} collapsed={collapsed} />
        <NavItem item={items[3]!} collapsed={collapsed} />
      </nav>
      <div className="sidebar-help">
        {!collapsed && me && (
          <>
            <Badge tone="ai">AI study tip</Badge>
            <p>
              {me.due_count > 0
                ? `Review ${me.due_count} card${me.due_count === 1 ? '' : 's'} today to stay on track.`
                : me.subjects.length ? 'You’re all caught up. Ask XP about anything in your materials.' : 'Create a subject and upload a file to get started.'}
            </p>
          </>
        )}
        <a className="sidebar-user" href={oldPages.settings} title={collapsed ? 'Settings' : undefined}>
          {me ? <Avatar small initials={initials(name)} /> : <Skeleton className="skeleton-avatar" />}
          <div>
            {!collapsed && me && (
              <>
                <strong>{name}</strong>
                <span>{me.email || me.username}</span>
              </>
            )}
          </div>
          {!collapsed && <Icon name="more" />}
        </a>
      </div>
    </aside>
  )
}
