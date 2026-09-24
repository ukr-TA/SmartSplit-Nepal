import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CalendarDays, Plus, Search, Users } from 'lucide-react'
import { groupApi } from '../api/services'
import GroupFormModal from '../components/GroupFormModal'
import { AvatarStack, CardSkeleton, EmptyState, ErrorState, Money, PageHeader } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { GROUP_TYPES, groupTypeOf } from '../utils/constants'
import { formatShortDate, toNumber } from '../utils/format'

export default function Groups({ createOpen = false }) {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useApi(() => groupApi.list(), [])
  const [creating, setCreating] = useState(createOpen)
  const [query, setQuery] = useState('')
  const [type, setType] = useState('all')

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data || []).filter(
      (g) => (type === 'all' || g.group_type === type) && (!q || g.name.toLowerCase().includes(q)),
    )
  }, [data, query, type])

  const closeCreate = () => {
    setCreating(false)
    if (createOpen) navigate('/groups', { replace: true })
  }

  return (
    <div className="page">
      <PageHeader
        title="My Groups"
        subtitle="Trips, flats, college projects and friends - each with its own balances."
        actions={
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            <Plus size={18} /> Create group
          </button>
        }
      />

      {(data?.length || 0) > 0 && (
        <div className="filter-bar">
          <div className="search-box">
            <Search size={16} />
            <input placeholder="Search groups" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="chips">
            <button className={`chip ${type === 'all' ? 'active' : ''}`} onClick={() => setType('all')}>All</button>
            {GROUP_TYPES.filter((t) => data.some((g) => g.group_type === t.value)).map((t) => (
              <button key={t.value} className={`chip ${type === t.value ? 'active' : ''}`} onClick={() => setType(t.value)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : loading ? (
        <div className="group-grid">
          {[1, 2, 3].map((i) => <CardSkeleton key={i} />)}
        </div>
      ) : data.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Users}
            title="No groups yet"
            message="Create a group like “Pokhara Trip” or “Kathmandu Flat” to start splitting."
            action={<button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} /> Create your first group</button>}
          />
        </div>
      ) : groups.length === 0 ? (
        <p className="muted center">No groups match your search.</p>
      ) : (
        <div className="group-grid">
          {groups.map((g) => {
            const t = groupTypeOf(g.group_type)
            const Icon = t.icon
            const net = toNumber(g.my_net)
            return (
              <Link key={g.id} to={`/groups/${g.id}`} className="card group-card">
                <div className="group-card-top">
                  <span className={`group-icon type-${g.group_type}`}><Icon size={22} /></span>
                  <div className="grow">
                    <h3>{g.name}</h3>
                    <small className="muted">
                      {t.label}
                      {g.is_trip && g.start_date && (
                        <> · <CalendarDays size={12} /> {formatShortDate(g.start_date)}{g.end_date ? ` – ${formatShortDate(g.end_date)}` : ''}</>
                      )}
                    </small>
                  </div>
                  {g.is_trip && <span className="pill">Trip</span>}
                </div>
                {g.description && <p className="muted small clamp">{g.description}</p>}
                <div className="group-card-mid">
                  <div>
                    <small className="muted">Total spent</small>
                    <Money value={g.total_spent} className="strong" />
                  </div>
                  <div className="right">
                    <small className="muted">{net > 0 ? 'You receive' : net < 0 ? 'You give' : 'Your balance'}</small>
                    {net === 0 ? <strong className="muted">Settled</strong> : <Money value={Math.abs(net)} tone={net > 0 ? 'receive' : 'give'} className="strong" />}
                  </div>
                </div>
                <div className="group-card-foot">
                  <AvatarStack users={g.members_preview} max={5} />
                  <small className="muted">{g.member_count} members · {g.expense_count} expenses</small>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {creating && (
        <GroupFormModal
          onClose={closeCreate}
          onSaved={(g) => navigate(`/groups/${g.id}/members?add=1`)}
        />
      )}
    </div>
  )
}
