import { useMe } from '../../lib/api'
import { Icon } from '../../ui/Icon'
import { Skeleton } from '../../ui/primitives'

export function greeting(hour = new Date().getHours()) {
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export function todayLabel(date = new Date()) {
  const weekday = date.toLocaleDateString('en-GB', { weekday: 'long' })
  const day = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })
  return `${weekday}, ${day}`.toUpperCase()
}

// shortcut: placeholder body until step 2 builds the real "Today" queue (/api/home/).
export function Today() {
  const me = useMe()
  return (
    <div className="page-content">
      <div className="page-intro">
        <div>
          <p className="overline">{todayLabel()}</p>
          {me.data
            ? <h1>{greeting()}, {me.data.first_name || me.data.username}</h1>
            : <h1><Skeleton className="skeleton-value" /></h1>}
          <p>Here’s the most useful work to do today.</p>
        </div>
      </div>
      <div className="empty-state">
        <span className="empty-icon"><Icon name="layers" /></span>
        <h2>Your study queue is on its way</h2>
        <p>Due cards, suggestions and recent chats will appear here.</p>
      </div>
    </div>
  )
}
