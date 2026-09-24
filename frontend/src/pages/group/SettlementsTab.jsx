import { useState } from 'react'
import { HandCoins } from 'lucide-react'
import { groupApi, settlementApi } from '../../api/services'
import SettlementItem from '../../components/SettlementItem'
import SuggestionList from '../../components/SuggestionList'
import { CardSkeleton, EmptyState, ErrorState, Money } from '../../components/ui'
import { useApi } from '../../hooks/useApi'

export default function SettlementsTab({ group, user, version }) {
  const history = useApi(() => settlementApi.list({ group: group.id }), [group.id, version])
  const plan = useApi(() => groupApi.suggestions(group.id), [group.id, version])
  const [filter, setFilter] = useState('all')

  if (history.error) return <ErrorState message={history.error} onRetry={history.reload} />

  const rows = (history.data || []).filter((s) => filter === 'all' || s.status === filter)
  const settledTotal = (history.data || [])
    .filter((s) => s.status === 'successful')
    .reduce((sum, s) => sum + Number(s.amount), 0)

  return (
    <div className="grid-1-2 align-start">
      <div className="card">
        <div className="card-head"><h3>Still to settle</h3></div>
        {plan.loading ? (
          <CardSkeleton />
        ) : (
          <SuggestionList groupId={group.id} suggestions={plan.data?.suggestions || []} userId={user.id} compact />
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Settlement history</h3>
          <small className="muted">Settled <Money value={settledTotal} className="strong" /></small>
        </div>
        <div className="chips">
          {['all', 'successful', 'pending', 'failed'].map((f) => (
            <button key={f} className={`chip ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {f[0].toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        {history.loading ? (
          <CardSkeleton />
        ) : rows.length === 0 ? (
          <EmptyState icon={HandCoins} title="No settlements yet" message="When someone pays back - by cash, eSewa or Khalti — it shows up here." />
        ) : (
          <ul className="settlement-list">
            {rows.map((s) => <SettlementItem key={s.id} s={s} userId={user.id} />)}
          </ul>
        )}
      </div>
    </div>
  )
}
