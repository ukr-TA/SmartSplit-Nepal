import { useMemo, useState } from 'react'
import { HandCoins } from 'lucide-react'
import { settlementApi } from '../api/services'
import SettlementItem from '../components/SettlementItem'
import { CardSkeleton, EmptyState, ErrorState, Money, PageHeader } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'

export default function Settlements() {
  const { user } = useAuth()
  const { data, loading, error, reload } = useApi(() => settlementApi.list(), [])
  const [status, setStatus] = useState('all')
  const [method, setMethod] = useState('all')
  const [who, setWho] = useState('all')

  const rows = useMemo(
    () =>
      (data || []).filter(
        (s) =>
          (status === 'all' || s.status === status) &&
          (method === 'all' || s.method === method) &&
          (who === 'all' || (who === 'paid' ? s.payer.id === user.id : s.recipient.id === user.id)),
      ),
    [data, status, method, who, user.id],
  )

  const ok = (data || []).filter((s) => s.status === 'successful')
  const paid = ok.filter((s) => s.payer.id === user.id).reduce((t, s) => t + Number(s.amount), 0)
  const received = ok.filter((s) => s.recipient.id === user.id).reduce((t, s) => t + Number(s.amount), 0)

  return (
    <div className="page">
      <PageHeader title="Settlement history" subtitle="Every cash, eSewa and Khalti settlement across your groups." />

      <div className="stat-grid three">
        <div className="stat-card tone-give">
          <span className="stat-label">You paid</span>
          <Money value={paid} className="stat-value" />
        </div>
        <div className="stat-card tone-receive">
          <span className="stat-label">You received</span>
          <Money value={received} className="stat-value" />
        </div>
        <div className="stat-card tone-brand">
          <span className="stat-label">Successful settlements</span>
          <strong className="stat-value">{ok.length}</strong>
        </div>
      </div>

      <div className="card">
        <div className="filter-bar wrap">
          <div className="chips">
            {[['all', 'Everything'], ['paid', 'I paid'], ['received', 'I received']].map(([v, l]) => (
              <button key={v} className={`chip ${who === v ? 'active' : ''}`} onClick={() => setWho(v)}>{l}</button>
            ))}
          </div>
          <select className="input select" value={method} onChange={(e) => setMethod(e.target.value)} aria-label="Payment method">
            <option value="all">All methods</option>
            <option value="esewa">eSewa</option>
            <option value="khalti">Khalti</option>
            <option value="cash">Cash</option>
          </select>
          <select className="input select" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="all">All statuses</option>
            <option value="successful">Successful</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading ? (
          <CardSkeleton rows={5} />
        ) : rows.length === 0 ? (
          <EmptyState icon={HandCoins} title="No settlements found" message="Settle a balance from any group to see it here." />
        ) : (
          <ul className="settlement-list">
            {rows.map((s) => <SettlementItem key={s.id} s={s} userId={user.id} showGroup />)}
          </ul>
        )}
      </div>
    </div>
  )
}
