import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, Plus, Receipt } from 'lucide-react'
import { expenseApi, groupApi } from '../../api/services'
import ExpenseList from '../../components/ExpenseList'
import ForecastCard from '../../components/ForecastCard'
import SuggestionList from '../../components/SuggestionList'
import { CardSkeleton, EmptyState, ErrorState, Money } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { toNumber } from '../../utils/format'

export default function OverviewTab({ group, user, refresh, version }) {
  const balances = useApi(() => groupApi.balances(group.id), [group.id, version])
  const expenses = useApi(() => expenseApi.list({ group: group.id, limit: 4 }), [group.id, version])

  if (balances.error) return <ErrorState message={balances.error} onRetry={balances.reload} />
  if (balances.loading || !balances.data) return <CardSkeleton rows={4} />

  const b = balances.data
  const net = toNumber(b.my_net)
  const myShare = b.members.find((m) => m.user.id === user.id)?.share ?? 0

  return (
    <div className="stack">
      <div className="stat-grid three">
        <div className="stat-card tone-brand">
          <span className="stat-label">Total group spending</span>
          <Money value={b.total_spent} className="stat-value" />
          <span className="stat-hint">{group.expense_count} expenses</span>
        </div>
        <div className="stat-card tone-neutral">
          <span className="stat-label">Your share</span>
          <Money value={myShare} className="stat-value" />
          <span className="stat-hint">what you consumed</span>
        </div>
        <div className={`stat-card tone-${net > 0 ? 'receive' : net < 0 ? 'give' : 'neutral'}`}>
          <span className="stat-label">{net > 0 ? 'You will receive' : net < 0 ? 'You need to give' : 'Your balance'}</span>
          {net === 0 ? <strong className="stat-value">Settled ✓</strong> : <Money value={Math.abs(net)} className="stat-value" />}
          <span className="stat-hint">after all settlements</span>
        </div>
      </div>

      <div className="grid-2 align-start">
        <div className="card">
          <div className="card-head">
            <h3>Smart settlement</h3>
            <Link to={`/groups/${group.id}/balances`} className="link-btn">Details <ArrowRight size={14} /></Link>
          </div>
          <SuggestionList groupId={group.id} suggestions={b.suggestions} userId={user.id} stats={b.stats} />
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Recent expenses</h3>
            <Link to={`/groups/${group.id}/expenses`} className="link-btn">All expenses <ArrowRight size={14} /></Link>
          </div>
          {expenses.loading ? (
            <CardSkeleton />
          ) : expenses.data?.length ? (
            <ExpenseList expenses={expenses.data} userId={user.id} onChanged={refresh} />
          ) : (
            <EmptyState
              icon={Receipt}
              title="No expenses yet"
              message={group.member_count < 2 ? 'Add members first, then split your first expense.' : 'Add the first shared expense.'}
              action={<Link to={`/split?group=${group.id}`} className="btn btn-primary btn-sm"><Plus size={15} /> Split Expense</Link>}
            />
          )}
        </div>
      </div>

      {toNumber(b.total_spent) > 0 && <ForecastCard group={group} version={version} />}

      {group.is_trip && toNumber(b.total_spent) > 0 && (
        <Link to={`/groups/${group.id}/analytics`} className="card trip-teaser">
          <BarChart3 size={22} />
          <span className="grow">
            <strong>Trip Analytics</strong>
            <small className="muted">Spending by category, member and day</small>
          </span>
          <ArrowRight size={18} />
        </Link>
      )}
    </div>
  )
}
