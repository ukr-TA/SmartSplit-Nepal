import { useState } from 'react'
import { Activity, Bell, CheckCheck } from 'lucide-react'
import { miscApi } from '../api/services'
import Timeline from '../components/Timeline'
import { CardSkeleton, EmptyState, ErrorState, PageHeader } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { timeAgo } from '../utils/format'

export default function ActivityPage() {
  const [tab, setTab] = useState('activity')
  const activity = useApi(() => miscApi.activity(), [])
  const notes = useApi(() => miscApi.notifications(), [])

  const markAll = async () => {
    await miscApi.markAllRead()
    notes.reload(true)
  }

  return (
    <div className="page">
      <PageHeader title="Activity" subtitle="What happened across your groups." />
      <nav className="tabs">
        <button className={`tab ${tab === 'activity' ? 'active' : ''}`} onClick={() => setTab('activity')}>Timeline</button>
        <button className={`tab ${tab === 'notifications' ? 'active' : ''}`} onClick={() => setTab('notifications')}>
          Notifications {notes.data?.unread_count > 0 && <span className="pill pill-give tiny">{notes.data.unread_count}</span>}
        </button>
      </nav>

      <div className="card">
        {tab === 'activity' ? (
          activity.error ? (
            <ErrorState message={activity.error} onRetry={activity.reload} />
          ) : activity.loading ? (
            <CardSkeleton rows={6} />
          ) : activity.data.length ? (
            <Timeline items={activity.data} showGroup />
          ) : (
            <EmptyState icon={Activity} title="No activity yet" message="Create a group and add expenses to see them here." />
          )
        ) : notes.error ? (
          <ErrorState message={notes.error} onRetry={notes.reload} />
        ) : notes.loading ? (
          <CardSkeleton rows={6} />
        ) : notes.data.results.length ? (
          <>
            <div className="row-between">
              <span className="muted small">{notes.data.unread_count} unread</span>
              {notes.data.unread_count > 0 && (
                <button className="link-btn" onClick={markAll}><CheckCheck size={15} /> Mark all read</button>
              )}
            </div>
            <ul className="notification-list">
              {notes.data.results.map((n) => (
                <li key={n.id} className={n.is_read ? '' : 'unread'}>
                  <span className={`bell-dot kind-${n.kind}`} />
                  <div className="grow">
                    <strong>{n.title}</strong>
                    <p>{n.message}</p>
                    <small className="muted">{n.group_name ? `${n.group_name} · ` : ''}{timeAgo(n.created_at)}</small>
                  </div>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <EmptyState icon={Bell} title="No notifications" message="You'll be notified when friends add expenses or pay you." />
        )}
      </div>
    </div>
  )
}
